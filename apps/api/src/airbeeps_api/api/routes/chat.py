from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.chat import (
    ChatCreateRequest,
    ChatCreateResponse,
    ChatHistoryResponse,
    ChatMessageCreateRequest,
    ChatTurnResponse,
)
from services.chat.context import ChatContextBuilder
from services.chat.workflow import ChatWorkflowError, ChatWorkflowService
from services.usage.service import UsageService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_service(
    *,
    session: AsyncSession,
    container: ServiceContainer,
) -> ChatWorkflowService:
    return ChatWorkflowService(
        session=session,
        llm=container.llm,
        model_router=container.model_router,
        rag=container.rag,
        memory=container.memory,
        usage=UsageService(
            session=session,
            requests_per_minute=container.settings.workspace_requests_per_minute,
            estimated_cost_per_1k_tokens=container.settings.llm_estimated_cost_per_1k_tokens,
        ),
        tools=container.tools,
        context_builder=ChatContextBuilder(
            system_prompt=container.settings.chat_system_prompt,
            max_messages=container.settings.chat_context_window_messages,
        ),
        retrieval_top_k=container.settings.rag_top_k,
        memory_top_k=container.settings.memory_top_k,
        max_tool_iterations=container.settings.runtime_tool_max_iterations,
    )


@router.post("/sessions", response_model=ChatCreateResponse)
async def create_chat_session(
    request: ChatCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> ChatCreateResponse:
    service = _build_service(session=session, container=container)
    try:
        return await service.create_chat(request=request, user=user)
    except ChatWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/sessions/{chat_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_messages(
    chat_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> ChatHistoryResponse:
    service = _build_service(session=session, container=container)
    try:
        return await service.get_history(chat_id=chat_id, workspace_id=workspace_id, user=user)
    except ChatWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/sessions/{chat_id}/messages", response_model=ChatTurnResponse)
async def post_chat_message(
    chat_id: str,
    workspace_id: str,
    request: ChatMessageCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> ChatTurnResponse:
    service = _build_service(session=session, container=container)
    try:
        return await service.execute_turn(
            chat_id=chat_id,
            workspace_id=workspace_id,
            request=request,
            user=user,
        )
    except ChatWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/sessions/{chat_id}/messages/stream")
async def stream_chat_message(
    chat_id: str,
    workspace_id: str,
    request: ChatMessageCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> StreamingResponse:
    service = _build_service(session=session, container=container)
    stream = service.stream_turn(
        chat_id=chat_id,
        workspace_id=workspace_id,
        request=request,
        user=user,
    )
    return StreamingResponse(stream, media_type="text/event-stream")
