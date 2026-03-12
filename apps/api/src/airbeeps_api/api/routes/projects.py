from fastapi import APIRouter, Depends, HTTPException
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.project import ProjectCreateRequest, ProjectResponse
from services.platform.service import PlatformService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    service = PlatformService(session)
    try:
        project = await service.create_project(
            workspace_id=request.workspace_id,
            name=request.name,
            description=request.description,
            user_id=user.user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return ProjectResponse(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        description=project.description,
        created_by=project.created_by,
        created_at=project.created_at.isoformat(),
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    service = PlatformService(session)
    try:
        projects = await service.list_projects(workspace_id=workspace_id, user_id=user.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return [
        ProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            created_by=project.created_by,
            created_at=project.created_at.isoformat(),
        )
        for project in projects
    ]
