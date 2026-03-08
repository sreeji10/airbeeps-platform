from fastapi import APIRouter, Depends
from libs.schemas.auth import AuthenticatedUser, CurrentUserResponse
from services.platform.service import PlatformService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    service = PlatformService(session)
    workspaces = await service.list_user_workspaces(user_id=user.user_id)
    return CurrentUserResponse(user_id=user.user_id, email=user.email, workspaces=workspaces)
