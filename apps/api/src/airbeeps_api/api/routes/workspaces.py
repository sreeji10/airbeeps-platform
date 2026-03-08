from fastapi import APIRouter, Depends
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from services.platform.service import PlatformService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    service = PlatformService(session)
    workspace = await service.create_workspace(name=request.name, user_id=user.user_id)
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_by=workspace.created_by,
        created_at=workspace.created_at.isoformat(),
    )
