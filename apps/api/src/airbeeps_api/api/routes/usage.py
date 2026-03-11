from fastapi import APIRouter, Depends, HTTPException
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.usage import UsageSummaryResponse
from services.platform.service import PlatformService
from services.usage.service import UsageService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    workspace_id: str,
    project_id: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> UsageSummaryResponse:
    platform = PlatformService(session)
    try:
        await platform.ensure_workspace_access(workspace_id=workspace_id, user_id=user.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    usage = UsageService(
        session=session,
        requests_per_minute=container.settings.workspace_requests_per_minute,
        estimated_cost_per_1k_tokens=container.settings.llm_estimated_cost_per_1k_tokens,
    )
    summary = await usage.summarize(workspace_id=workspace_id, project_id=project_id)
    return UsageSummaryResponse.model_validate(summary)
