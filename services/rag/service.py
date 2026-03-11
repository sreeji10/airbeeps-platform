from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import Dataset, DatasetChunk, DatasetFile
from libs.embeddings.base import EmbeddingClient
from libs.schemas.rag import RetrievedChunk
from services.ingestion.text import chunk_text, extract_text
from services.storage.supabase_storage import SupabaseStorageService


@dataclass
class IngestionResult:
    dataset_id: str
    accepted_files: int
    chunk_count: int


class RagService:
    async def retrieve(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        query: str,
        dataset_ids: list[str],
        top_k: int,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError

    async def ingest_dataset(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        dataset_id: str,
    ) -> IngestionResult:
        raise NotImplementedError


@dataclass
class PostgresRagService(RagService):
    embeddings: EmbeddingClient
    storage: SupabaseStorageService
    default_top_k: int = 5
    chunk_size: int = 1200
    chunk_overlap: int = 200

    async def ingest_dataset(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        dataset_id: str,
    ) -> IngestionResult:
        dataset = await self._get_dataset(
            session=session,
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
        if dataset is None:
            raise ValueError("Dataset not found in project")

        files = await self._get_dataset_files(
            session=session,
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
        if not files:
            raise ValueError("Dataset has no files")

        await session.execute(
            delete(DatasetChunk).where(
                DatasetChunk.workspace_id == workspace_id,
                DatasetChunk.project_id == project_id,
                DatasetChunk.dataset_id == dataset_id,
            )
        )

        total_chunks = 0
        for file_row in files:
            file_bytes = await self.storage.download_bytes(
                bucket=file_row.storage_bucket,
                path=file_row.storage_path,
            )
            text = extract_text(
                filename=file_row.filename,
                content_type=file_row.content_type,
                content=file_bytes,
            )
            chunks = chunk_text(
                text,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
            )
            if not chunks:
                continue

            vectors = await self.embeddings.embed_texts(chunks)
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
                if not vector:
                    continue
                session.add(
                    DatasetChunk(
                        workspace_id=workspace_id,
                        project_id=project_id,
                        dataset_id=dataset_id,
                        dataset_file_id=file_row.id,
                        chunk_index=idx,
                        content=chunk,
                        embedding=vector,
                        chunk_metadata={
                            "filename": file_row.filename,
                            "storage_path": file_row.storage_path,
                        },
                    )
                )
                total_chunks += 1

        dataset.status = "ready" if total_chunks > 0 else "empty"
        session.add(dataset)
        await session.commit()
        return IngestionResult(
            dataset_id=dataset_id,
            accepted_files=len(files),
            chunk_count=total_chunks,
        )

    async def retrieve(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        query: str,
        dataset_ids: list[str],
        top_k: int,
    ) -> list[RetrievedChunk]:
        limit = max(1, min(top_k, self.default_top_k))
        selected_dataset_ids = dataset_ids or await self._resolve_ready_datasets(
            session=session,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        if not selected_dataset_ids:
            return []

        query_vectors = await self.embeddings.embed_texts([query])
        if not query_vectors or not query_vectors[0]:
            return []
        query_vector = query_vectors[0]

        result = await session.execute(
            select(DatasetChunk).where(
                DatasetChunk.workspace_id == workspace_id,
                DatasetChunk.project_id == project_id,
                DatasetChunk.dataset_id.in_(selected_dataset_ids),
            )
        )
        chunks = result.scalars().all()
        scored: list[tuple[float, DatasetChunk]] = []
        for chunk in chunks:
            score = _cosine_similarity(query_vector, chunk.embedding)
            scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_items = scored[:limit]
        return [
            RetrievedChunk(
                dataset_id=item.dataset_id,
                chunk_id=item.id,
                score=max(0.0, min(1.0, (score + 1.0) / 2.0)),
                content=item.content,
                citation=f"{item.chunk_metadata.get('filename', 'dataset')}#{item.chunk_index}",
            )
            for score, item in top_items
        ]

    async def _get_dataset(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        dataset_id: str,
    ) -> Dataset | None:
        result = await session.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.workspace_id == workspace_id,
                Dataset.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_dataset_files(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        dataset_id: str,
    ) -> list[DatasetFile]:
        result = await session.execute(
            select(DatasetFile).where(
                DatasetFile.workspace_id == workspace_id,
                DatasetFile.project_id == project_id,
                DatasetFile.dataset_id == dataset_id,
            )
        )
        return list(result.scalars().all())

    async def _resolve_ready_datasets(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
    ) -> list[str]:
        result = await session.execute(
            select(Dataset.id).where(
                Dataset.workspace_id == workspace_id,
                Dataset.project_id == project_id,
                Dataset.status == "ready",
            )
        )
        return list(result.scalars().all())


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot = sum(lhs * rhs for lhs, rhs in zip(left, right, strict=False))
    return dot / (left_norm * right_norm)
