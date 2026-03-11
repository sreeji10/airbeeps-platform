from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from libs.schemas.rag import RetrievedChunk
from services.rag.service import RagService


@dataclass
class RetrievalTool:
    rag: RagService

    async def search(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        query: str,
        dataset_ids: list[str],
        top_k: int,
    ) -> list[RetrievedChunk]:
        return await self.rag.retrieve(
            session=session,
            workspace_id=workspace_id,
            project_id=project_id,
            query=query,
            dataset_ids=dataset_ids,
            top_k=top_k,
        )
