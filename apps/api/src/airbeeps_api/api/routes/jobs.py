from fastapi import APIRouter, Depends, HTTPException
from libs.db.models import BackgroundJob
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.job import JobCreateRequest, JobRead
from services.jobs.service import JobService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return value


def _to_read(job: BackgroundJob) -> JobRead:
    return JobRead(
        id=job.id,
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        kind=job.kind,
        status=job.status,
        payload=_as_dict(job.payload),
        result=_as_dict(job.result),
        error=job.error,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        run_after=job.run_after.isoformat(),
        created_by=job.created_by,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.post("", response_model=JobRead)
async def create_job(
    request: JobCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    service = JobService(session)
    try:
        row = await service.enqueue(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _to_read(row)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    service = JobService(session)
    row = await service.get_job(job_id=job_id, workspace_id=workspace_id, user=user)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_read(row)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    workspace_id: str,
    project_id: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "desc",
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[JobRead]:
    service = JobService(session)
    bounded_limit = min(max(limit, 1), 200)
    bounded_offset = max(offset, 0)
    rows = await service.list_jobs(
        workspace_id=workspace_id,
        project_id=project_id,
        user=user,
        status=status,
        kind=kind,
        limit=bounded_limit,
        offset=bounded_offset,
        sort_desc=sort != "asc",
    )
    return [_to_read(row) for row in rows]
