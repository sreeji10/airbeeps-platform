from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import Chat, Message, Plan, Project, Run
from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.auth import AuthenticatedUser
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


class ChatWorkflowError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ChatWorkflowService:
    session: AsyncSession
    llm: LLMClient
    context_builder: ChatContextBuilder

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
        plan = await self._create_plan(chat=chat, user=user, prompt=request.content)
        run = await self._create_run(chat=chat, plan=plan, prompt=request.content)
        await self._set_run_state(run=run, plan=plan, status="running")

        try:
            context_messages = await self._build_context(
                chat_id=chat.id, workspace_id=workspace_id
            )
            assistant_text = await self.llm.complete(context_messages)
            assistant_message = await self._store_message(
                chat_id=chat.id,
                workspace_id=workspace_id,
                role="assistant",
                content=assistant_text,
                created_by=user.user_id,
            )
            await self._complete_run(run=run, plan=plan, output_text=assistant_text)
        except Exception as exc:
            await self._fail_run(run=run, plan=plan, error=str(exc))
            raise

        return ChatTurnResponse(
            chat_id=chat.id,
            user_message=user_message,
            assistant_message=assistant_message,
            plan_id=plan.id,
            run_id=run.id,
            run_status=run.status,
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
        plan = await self._create_plan(chat=chat, user=user, prompt=request.content)
        run = await self._create_run(chat=chat, plan=plan, prompt=request.content)
        await self._set_run_state(run=run, plan=plan, status="running")

        buffered: list[str] = []
        try:
            context_messages = await self._build_context(
                chat_id=chat.id, workspace_id=workspace_id
            )
            async for token in self.llm.stream(context_messages):
                buffered.append(token)
                yield self._sse_event("token", {"token": token, "run_id": run.id})

            assistant_text = "".join(buffered)
            assistant_message = await self._store_message(
                chat_id=chat.id,
                workspace_id=workspace_id,
                role="assistant",
                content=assistant_text,
                created_by=user.user_id,
            )
            await self._complete_run(run=run, plan=plan, output_text=assistant_text)
            yield self._sse_event(
                "done",
                {
                    "chat_id": chat.id,
                    "run_id": run.id,
                    "plan_id": plan.id,
                    "assistant_message_id": assistant_message.id,
                    "status": run.status,
                },
            )
        except Exception as exc:
            await self._fail_run(run=run, plan=plan, error=str(exc))
            yield self._sse_event("error", {"message": str(exc), "run_id": run.id})

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

    async def _create_plan(
        self, *, chat: Chat, user: AuthenticatedUser, prompt: str
    ) -> Plan:
        plan = Plan(
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            chat_id=chat.id,
            status="created",
            payload={
                "type": "chat_turn",
                "steps": ["build_context", "llm_generate", "persist_response"],
                "prompt": prompt,
            },
            created_by=user.user_id,
        )
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def _create_run(self, *, chat: Chat, plan: Plan, prompt: str) -> Run:
        run = Run(
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            plan_id=plan.id,
            status="created",
            input_payload={"chat_id": chat.id, "prompt": prompt},
            output_payload={},
            started_at=_utc_now(),
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def _set_run_state(self, *, run: Run, plan: Plan, status: str) -> None:
        run.status = status
        plan.status = status
        self.session.add(run)
        self.session.add(plan)
        await self.session.commit()

    async def _complete_run(self, *, run: Run, plan: Plan, output_text: str) -> None:
        run.status = "completed"
        run.output_payload = {"response": output_text}
        run.completed_at = _utc_now()
        plan.status = "completed"
        self.session.add(run)
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(run)

    async def _fail_run(self, *, run: Run, plan: Plan, error: str) -> None:
        run.status = "failed"
        run.output_payload = {"error": error}
        run.completed_at = _utc_now()
        plan.status = "failed"
        self.session.add(run)
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(run)

    def _sse_event(self, event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
