from fastapi import APIRouter, Depends, HTTPException
from libs.db.models import AgentConfig
from libs.schemas.agent import AgentCreateRequest, AgentRead, AgentUpdateRequest
from libs.schemas.auth import AuthenticatedUser
from services.agents.service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_read(row: AgentConfig) -> AgentRead:
    return AgentRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        name=row.name,
        description=row.description,
        planner_model=row.planner_model,
        generation_model=row.generation_model,
        fallback_model=row.fallback_model,
        prompt_template_id=row.prompt_template_id,
        enabled_tools=list(row.enabled_tools),
        dataset_ids=list(row.dataset_ids),
        execution_limits=dict(row.execution_limits),
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )


@router.post("", response_model=AgentRead)
async def create_agent(
    request: AgentCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRead:
    service = AgentService(session)
    try:
        agent = await service.create_agent(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _to_read(agent)


@router.get("", response_model=list[AgentRead])
async def list_agents(
    workspace_id: str,
    project_id: str,
    include_archived: bool = False,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentRead]:
    service = AgentService(session)
    rows = await service.list_agents(
        workspace_id=workspace_id,
        project_id=project_id,
        user=user,
        include_archived=include_archived,
    )
    return [_to_read(row) for row in rows]


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRead:
    service = AgentService(session)
    row = await service.get_agent(agent_id=agent_id, workspace_id=workspace_id, user=user)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_read(row)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str,
    workspace_id: str,
    request: AgentUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRead:
    service = AgentService(session)
    row = await service.update_agent(
        agent_id=agent_id,
        workspace_id=workspace_id,
        request=request,
        user=user,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_read(row)


@router.delete("/{agent_id}", response_model=AgentRead)
async def archive_agent(
    agent_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRead:
    service = AgentService(session)
    row = await service.archive_agent(
        agent_id=agent_id,
        workspace_id=workspace_id,
        user=user,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_read(row)
