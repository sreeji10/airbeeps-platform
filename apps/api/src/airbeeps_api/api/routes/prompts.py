from fastapi import APIRouter, Depends, HTTPException
from libs.db.models import PromptTemplate
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.prompt import PromptTemplateCreateRequest, PromptTemplateRead
from services.prompts.service import PromptService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _to_read(row: PromptTemplate) -> PromptTemplateRead:
    return PromptTemplateRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        name=row.name,
        version=row.version,
        template=row.template,
        variables=list(row.variables),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )


@router.post("", response_model=PromptTemplateRead)
async def create_prompt_template(
    request: PromptTemplateCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateRead:
    service = PromptService(session)
    try:
        row = await service.create_template(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _to_read(row)


@router.get("", response_model=list[PromptTemplateRead])
async def list_prompt_templates(
    workspace_id: str,
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PromptTemplateRead]:
    service = PromptService(session)
    rows = await service.list_templates(
        workspace_id=workspace_id,
        project_id=project_id,
        user=user,
    )
    return [_to_read(row) for row in rows]
