from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import Chat, Message, Project
from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.auth import AuthenticatedUser
from libs.tools.registry import ToolRegistry
from libs.schemas.chat import (
    ChatCreateRequest,
    ChatCreateResponse,
    ChatHistoryResponse,
    ChatMessageCreateRequest,
    ChatMessageRead,
    ChatTurnResponse,
)
from services.chat.context import ChatContextBuilder
from services.platform.service import PlatformService
from services.rag.service import RagService
from services.runtime.executor import RuntimeExecutor
from services.runtime.planner import RuntimePlanner
from services.runtime.service import RuntimeServiceImpl


class ChatWorkflowError(Exception):
    pass


@dataclass
class ChatWorkflowService:
    session: AsyncSession
    llm: LLMClient
    rag: RagService
    tools: ToolRegistry
    context_builder: ChatContextBuilder
    retrieval_top_k: int = 5
    max_tool_iterations: int = 4

    async def create_chat(
        self, request: ChatCreateRequest, user: AuthenticatedUser
    ) -> ChatCreateResponse:
        platform_service = PlatformService(self.session)
        await platform_service.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )

        project = await self._get_project(request.project_id, request.workspace_id)
        if project is None:
            raise ChatWorkflowError("Project not found in workspace")

        chat = Chat(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            title=request.title,
            created_by=user.user_id,
        )
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return ChatCreateResponse(
            chat_id=chat.id,
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            title=chat.title,
            created_at=chat.created_at.isoformat(),
        )

    async def get_history(
        self, *, chat_id: str, workspace_id: str, user: AuthenticatedUser
    ) -> ChatHistoryResponse:
        await self._ensure_chat_access(
            chat_id=chat_id, workspace_id=workspace_id, user=user
        )
        messages = await self._load_messages(chat_id=chat_id, workspace_id=workspace_id)
        return ChatHistoryResponse(chat_id=chat_id, messages=messages)

    async def execute_turn(
        self,
        *,
        chat_id: str,
        workspace_id: str,
        request: ChatMessageCreateRequest,
        user: AuthenticatedUser,
    ) -> ChatTurnResponse:
        chat = await self._ensure_chat_access(
            chat_id=chat_id, workspace_id=workspace_id, user=user
        )
        user_message = await self._store_message(
            chat_id=chat.id,
            workspace_id=workspace_id,
            role="user",
            content=request.content,
            created_by=user.user_id,
        )

        context_messages = await self._build_context(
            chat_id=chat.id, workspace_id=workspace_id
        )
        runtime = RuntimeServiceImpl(
            session=self.session,
            planner=RuntimePlanner(self.llm, tools=self.tools),
            executor=RuntimeExecutor(
                llm=self.llm,
                tools=self.tools,
                retrieval_top_k=self.retrieval_top_k,
                max_tool_iterations=self.max_tool_iterations,
            ),
        )
        result = await runtime.execute_turn(
            chat=chat,
            user=user,
            user_message=request.content,
            context_messages=context_messages,
            dataset_ids=request.dataset_ids,
        )

        assistant_message = await self._store_message(
            chat_id=chat.id,
            workspace_id=workspace_id,
            role="assistant",
            content=result.response,
            created_by=user.user_id,
        )

        return ChatTurnResponse(
            chat_id=chat.id,
            user_message=user_message,
            assistant_message=assistant_message,
            plan_id=result.plan_id,
            run_id=result.run_id,
            run_status=result.run_status,
        )

    async def stream_turn(
        self,
        *,
        chat_id: str,
        workspace_id: str,
        request: ChatMessageCreateRequest,
        user: AuthenticatedUser,
    ) -> AsyncIterator[str]:
        chat = await self._ensure_chat_access(
            chat_id=chat_id, workspace_id=workspace_id, user=user
        )
        await self._store_message(
            chat_id=chat.id,
            workspace_id=workspace_id,
            role="user",
            content=request.content,
            created_by=user.user_id,
        )

        context_messages = await self._build_context(
            chat_id=chat.id, workspace_id=workspace_id
        )
        runtime = RuntimeServiceImpl(
            session=self.session,
            planner=RuntimePlanner(self.llm, tools=self.tools),
            executor=RuntimeExecutor(
                llm=self.llm,
                tools=self.tools,
                retrieval_top_k=self.retrieval_top_k,
                max_tool_iterations=self.max_tool_iterations,
            ),
        )

        async for event in runtime.stream_turn(
            chat=chat,
            user=user,
            user_message=request.content,
            context_messages=context_messages,
            dataset_ids=request.dataset_ids,
        ):
            event_type = str(event.get("type", ""))
            event_data = cast(dict[str, object], event.get("data", {}))

            if event_type == "token":
                yield self._sse_event("token", event_data)
                continue

            if event_type == "status":
                yield self._sse_event("status", event_data)
                continue

            if event_type == "completed":
                response_text = str(event_data.get("response", ""))
                assistant_message = await self._store_message(
                    chat_id=chat.id,
                    workspace_id=workspace_id,
                    role="assistant",
                    content=response_text,
                    created_by=user.user_id,
                )
                yield self._sse_event(
                    "done",
                    {
                        "chat_id": chat.id,
                        "run_id": event_data.get("run_id"),
                        "plan_id": event_data.get("plan_id"),
                        "assistant_message_id": assistant_message.id,
                        "status": event_data.get("status", "completed"),
                    },
                )
                continue

            if event_type == "error":
                yield self._sse_event("error", event_data)

    async def _ensure_chat_access(
        self, *, chat_id: str, workspace_id: str, user: AuthenticatedUser
    ) -> Chat:
        platform_service = PlatformService(self.session)
        await platform_service.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id, Chat.workspace_id == workspace_id)
        )
        chat = result.scalar_one_or_none()
        if chat is None:
            raise ChatWorkflowError("Chat not found in workspace")
        return chat

    async def _get_project(self, project_id: str, workspace_id: str) -> Project | None:
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id, Project.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def _load_messages(
        self, *, chat_id: str, workspace_id: str
    ) -> list[ChatMessageRead]:
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id, Message.workspace_id == workspace_id)
            .order_by(Message.created_at.asc())
        )
        rows = result.scalars().all()
        return [
            ChatMessageRead(
                id=row.id,
                role=cast(Literal["user", "assistant", "system"], row.role),
                content=row.content,
                created_by=row.created_by,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]

    async def _build_context(
        self, *, chat_id: str, workspace_id: str
    ) -> list[LLMMessage]:
        history = await self._load_messages(chat_id=chat_id, workspace_id=workspace_id)
        return self.context_builder.build(history)

    async def _store_message(
        self,
        *,
        chat_id: str,
        workspace_id: str,
        role: str,
        content: str,
        created_by: str,
    ) -> ChatMessageRead:
        message = Message(
            chat_id=chat_id,
            workspace_id=workspace_id,
            role=role,
            content=content,
            created_by=created_by,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return ChatMessageRead(
            id=message.id,
            role=cast(Literal["user", "assistant", "system"], message.role),
            content=message.content,
            created_by=message.created_by,
            created_at=message.created_at.isoformat(),
        )

    def _sse_event(self, event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
