from fastapi import APIRouter, Depends, HTTPException
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.ingestion import IngestDatasetRequest, IngestDatasetResponse
from libs.schemas.job import JobCreateRequest, JobRead
from services.jobs.service import JobService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/ingest", response_model=IngestDatasetResponse)
async def ingest_dataset(
    request: IngestDatasetRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> IngestDatasetResponse:
    try:
        return await container.ingestion.ingest(
            session=session,
            request=request,
            user=user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ingest/jobs", response_model=JobRead)
async def enqueue_ingest_dataset(
    request: IngestDatasetRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    jobs = JobService(session)
    row = await jobs.enqueue(
        request=JobCreateRequest(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            kind="dataset_ingestion",
            payload=request.model_dump(),
        ),
        user=user,
    )
    return JobRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        kind=row.kind,
        status=row.status,
        payload=dict(row.payload),
        result=dict(row.result),
        error=row.error,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        run_after=row.run_after.isoformat(),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )
