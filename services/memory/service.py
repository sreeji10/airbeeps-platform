from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import MemoryEntry
from libs.embeddings.base import EmbeddingClient
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.memory import MemoryCreateRequest
from services.platform.service import PlatformService


def _cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    if not lhs or not rhs:
        return 0.0
    size = min(len(lhs), len(rhs))
    if size == 0:
        return 0.0
    dot = 0.0
    lhs_norm = 0.0
    rhs_norm = 0.0
    for index in range(size):
        a = lhs[index]
        b = rhs[index]
        dot += a * b
        lhs_norm += a * a
        rhs_norm += b * b
    denom = math.sqrt(lhs_norm) * math.sqrt(rhs_norm)
    if denom == 0:
        return 0.0
    return dot / denom


@dataclass(frozen=True)
class RetrievedMemory:
    id: str
    content: str
    score: float
    metadata: dict[str, object]
    created_by: str
    created_at: str


@dataclass
class MemoryService:
    embeddings: EmbeddingClient

    async def add_memory(
        self,
        *,
        session: AsyncSession,
        request: MemoryCreateRequest,
        user: AuthenticatedUser,
    ) -> MemoryEntry:
        platform = PlatformService(session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        vectors = await self.embeddings.embed_texts([request.content])
        vector = vectors[0] if vectors else []
        entry = MemoryEntry(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            agent_id=request.agent_id,
            source_chat_id=request.source_chat_id,
            content=request.content,
            embedding=vector,
            memory_metadata=request.metadata,
            created_by=user.user_id,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry

    async def search(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        query: str,
        top_k: int,
        user: AuthenticatedUser,
        agent_id: str | None = None,
    ) -> list[RetrievedMemory]:
        platform = PlatformService(session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        vectors = await self.embeddings.embed_texts([query])
        query_embedding = vectors[0] if vectors else []
        filters = [
            MemoryEntry.workspace_id == workspace_id,
            MemoryEntry.project_id == project_id,
        ]
        if agent_id is not None:
            filters.append(MemoryEntry.agent_id == agent_id)
        result = await session.execute(select(MemoryEntry).where(*filters))
        rows = result.scalars().all()
        ranked: list[tuple[float, MemoryEntry]] = []
        for row in rows:
            score = _cosine_similarity(query_embedding, row.embedding)
            ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[:top_k]
        return [
            RetrievedMemory(
                id=row.id,
                content=row.content,
                score=score,
                metadata=row.memory_metadata,
                created_by=row.created_by,
                created_at=row.created_at.isoformat(),
            )
            for score, row in selected
        ]

    async def delete_by_chat(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        chat_id: str,
    ) -> None:
        await session.execute(
            delete(MemoryEntry).where(
                MemoryEntry.workspace_id == workspace_id,
                MemoryEntry.source_chat_id == chat_id,
            )
        )
        await session.commit()
