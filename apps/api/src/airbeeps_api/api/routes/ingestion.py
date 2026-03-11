from fastapi import APIRouter, Depends, HTTPException
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.ingestion import IngestDatasetRequest, IngestDatasetResponse
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
