from fastapi import APIRouter, Depends, HTTPException
from libs.db.models import MemoryEntry
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.memory import MemoryCreateRequest, MemoryRead, MemorySearchRequest
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/memory", tags=["memory"])


def _to_read(entry: MemoryEntry, score: float | None = None) -> MemoryRead:
    return MemoryRead(
        id=entry.id,
        workspace_id=entry.workspace_id,
        project_id=entry.project_id,
        agent_id=entry.agent_id,
        source_chat_id=entry.source_chat_id,
        content=entry.content,
        score=score,
        metadata=dict(entry.memory_metadata),
        created_by=entry.created_by,
        created_at=entry.created_at.isoformat(),
    )


@router.post("", response_model=MemoryRead)
async def create_memory_entry(
    request: MemoryCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> MemoryRead:
    try:
        row = await container.memory.add_memory(session=session, request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _to_read(row)


@router.post("/search", response_model=list[MemoryRead])
async def search_memory(
    request: MemorySearchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> list[MemoryRead]:
    try:
        hits = await container.memory.search(
            session=session,
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
            user=user,
            agent_id=request.agent_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return [
        MemoryRead(
            id=item.id,
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            agent_id=request.agent_id,
            source_chat_id=None,
            content=item.content,
            score=item.score,
            metadata=item.metadata,
            created_by=item.created_by,
            created_at=item.created_at,
        )
        for item in hits
    ]
