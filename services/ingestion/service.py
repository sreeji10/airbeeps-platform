from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from libs.schemas.auth import AuthenticatedUser
from libs.schemas.ingestion import IngestDatasetRequest, IngestDatasetResponse
from libs.utils.ids import make_id
from services.platform.service import PlatformService
from services.rag.service import RagService


class IngestionService:
    async def ingest(
        self,
        *,
        session: AsyncSession,
        request: IngestDatasetRequest,
        user: AuthenticatedUser,
    ) -> IngestDatasetResponse:
        raise NotImplementedError


@dataclass
class SupabaseIngestionService(IngestionService):
    rag: RagService

    async def ingest(
        self,
        *,
        session: AsyncSession,
        request: IngestDatasetRequest,
        user: AuthenticatedUser,
    ) -> IngestDatasetResponse:
        platform = PlatformService(session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id,
            user_id=user.user_id,
        )

        result = await self.rag.ingest_dataset(
            session=session,
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            dataset_id=request.dataset_id,
        )

        return IngestDatasetResponse(
            job_id=make_id("ingest"),
            project_id=request.project_id,
            dataset_id=request.dataset_id,
            status="completed",
            accepted_files=result.accepted_files,
            chunk_count=result.chunk_count,
        )
