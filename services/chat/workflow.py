from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import AgentConfig, Chat, Message, Project, PromptTemplate
from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.memory import MemoryCreateRequest
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
from services.llm.instrumented import InstrumentedLLMClient
from services.llm.routing import ModelRouter
from services.memory.service import MemoryService
from services.platform.service import PlatformService
from services.prompts.service import PromptService
from services.rag.service import RagService
from services.usage.service import UsageService
from services.agents.service import AgentService
from services.runtime.executor import RuntimeExecutor
from services.runtime.planner import RuntimePlanner
from services.runtime.service import RuntimeServiceImpl


class ChatWorkflowError(Exception):
    pass


@dataclass
class ChatWorkflowService:
    session: AsyncSession
    llm: LLMClient
    model_router: ModelRouter
    rag: RagService
    memory: MemoryService
    usage: UsageService
    tools: ToolRegistry
    context_builder: ChatContextBuilder
    retrieval_top_k: int = 5
    memory_top_k: int = 4
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

    async def list_chats(
        self,
        *,
        workspace_id: str,
        project_id: str,
        user: AuthenticatedUser,
    ) -> list[ChatCreateResponse]:
        platform_service = PlatformService(self.session)
        await platform_service.ensure_workspace_access(
            workspace_id=workspace_id,
            user_id=user.user_id,
        )
        result = await self.session.execute(
            select(Chat)
            .where(
                Chat.workspace_id == workspace_id,
                Chat.project_id == project_id,
            )
            .order_by(Chat.created_at.desc())
        )
        chats = result.scalars().all()
        return [
            ChatCreateResponse(
                chat_id=chat.id,
                workspace_id=chat.workspace_id,
                project_id=chat.project_id,
                title=chat.title,
                created_at=chat.created_at.isoformat(),
            )
            for chat in chats
        ]

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
        await self.usage.enforce_workspace_rate_limit(workspace_id=workspace_id)
        await self.usage.record_request(
            workspace_id=workspace_id,
            project_id=chat.project_id,
            user_id=user.user_id,
        )

        agent = await self._resolve_agent(
            agent_id=request.agent_id,
            workspace_id=workspace_id,
            user=user,
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
        context_messages = await self._inject_agent_context(
            context_messages=context_messages,
            chat=chat,
            agent=agent,
            user=user,
            user_message=request.content,
        )
        dataset_ids = self._resolve_dataset_ids(request.dataset_ids, agent)
        tools = self._resolve_tools(agent)
        planner_llm, generation_llm = self._build_routed_clients(
            workspace_id=workspace_id,
            project_id=chat.project_id,
            user_id=user.user_id,
            agent=agent,
        )
        runtime = RuntimeServiceImpl(
            session=self.session,
            planner=RuntimePlanner(planner_llm, tools=tools),
            executor=RuntimeExecutor(
                llm=generation_llm,
                tools=tools,
                retrieval_top_k=self.retrieval_top_k,
                max_tool_iterations=self._resolve_max_tool_iterations(agent),
            ),
        )
        result = await runtime.execute_turn(
            chat=chat,
            user=user,
            user_message=request.content,
            context_messages=context_messages,
            dataset_ids=dataset_ids,
        )

        assistant_message = await self._store_message(
            chat_id=chat.id,
            workspace_id=workspace_id,
            role="assistant",
            content=result.response,
            created_by=user.user_id,
        )

        response = ChatTurnResponse(
            chat_id=chat.id,
            user_message=user_message,
            assistant_message=assistant_message,
            plan_id=result.plan_id,
            run_id=result.run_id,
            run_status=result.run_status,
        )
        await self._store_memory_from_turn(
            chat=chat,
            user=user,
            agent=agent,
            user_text=request.content,
            assistant_text=result.response,
        )
        return response

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
        await self.usage.enforce_workspace_rate_limit(workspace_id=workspace_id)
        await self.usage.record_request(
            workspace_id=workspace_id,
            project_id=chat.project_id,
            user_id=user.user_id,
        )

        agent = await self._resolve_agent(
            agent_id=request.agent_id,
            workspace_id=workspace_id,
            user=user,
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
        context_messages = await self._inject_agent_context(
            context_messages=context_messages,
            chat=chat,
            agent=agent,
            user=user,
            user_message=request.content,
        )
        dataset_ids = self._resolve_dataset_ids(request.dataset_ids, agent)
        tools = self._resolve_tools(agent)
        planner_llm, generation_llm = self._build_routed_clients(
            workspace_id=workspace_id,
            project_id=chat.project_id,
            user_id=user.user_id,
            agent=agent,
        )
        runtime = RuntimeServiceImpl(
            session=self.session,
            planner=RuntimePlanner(planner_llm, tools=tools),
            executor=RuntimeExecutor(
                llm=generation_llm,
                tools=tools,
                retrieval_top_k=self.retrieval_top_k,
                max_tool_iterations=self._resolve_max_tool_iterations(agent),
            ),
        )

        async for event in runtime.stream_turn(
            chat=chat,
            user=user,
            user_message=request.content,
            context_messages=context_messages,
            dataset_ids=dataset_ids,
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
                await self._store_memory_from_turn(
                    chat=chat,
                    user=user,
                    agent=agent,
                    user_text=request.content,
                    assistant_text=response_text,
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

    async def _resolve_agent(
        self,
        *,
        agent_id: str | None,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> AgentConfig | None:
        if agent_id is None:
            return None
        agent_service = AgentService(self.session)
        agent = await agent_service.get_agent(
            agent_id=agent_id,
            workspace_id=workspace_id,
            user=user,
        )
        if agent is None:
            raise ChatWorkflowError("Agent not found in workspace")
        if agent.status != "active":
            raise ChatWorkflowError("Agent is not active")
        return agent

    async def _inject_agent_context(
        self,
        *,
        context_messages: list[LLMMessage],
        chat: Chat,
        agent: AgentConfig | None,
        user: AuthenticatedUser,
        user_message: str,
    ) -> list[LLMMessage]:
        output = list(context_messages)
        if agent is not None:
            prompt_text = await self._resolve_prompt_text(
                agent=agent,
                chat=chat,
                user=user,
            )
            if output and output[0]["role"] == "system":
                output[0] = {"role": "system", "content": prompt_text}
        memories = await self.memory.search(
            session=self.session,
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            query=user_message,
            top_k=self.memory_top_k,
            user=user,
            agent_id=agent.id if agent is not None else None,
        )
        if memories:
            memory_block = "\n".join(
                f"- {item.content} (score={item.score:.3f})" for item in memories
            )
            output.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant long-term memory entries for this workspace/project:\n"
                        f"{memory_block}"
                    ),
                }
            )
        return output

    async def _resolve_prompt_text(
        self,
        *,
        agent: AgentConfig,
        chat: Chat,
        user: AuthenticatedUser,
    ) -> str:
        if agent.prompt_template_id is None:
            return self.context_builder.system_prompt
        result = await self.session.execute(
            select(PromptTemplate).where(
                PromptTemplate.id == agent.prompt_template_id,
                PromptTemplate.workspace_id == chat.workspace_id,
            )
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            return self.context_builder.system_prompt
        prompt_service = PromptService(self.session)
        return prompt_service.render(
            template=prompt,
            variables={
                "workspace_id": chat.workspace_id,
                "project_id": chat.project_id,
                "chat_id": chat.id,
                "user_id": user.user_id,
            },
        )

    def _resolve_dataset_ids(
        self,
        request_dataset_ids: list[str],
        agent: AgentConfig | None,
    ) -> list[str]:
        if request_dataset_ids:
            return request_dataset_ids
        if agent is not None and agent.dataset_ids:
            return list(agent.dataset_ids)
        return []

    def _resolve_tools(self, agent: AgentConfig | None) -> ToolRegistry:
        if agent is None or not agent.enabled_tools:
            return self.tools
        return self.tools.filtered(agent.enabled_tools)

    def _resolve_max_tool_iterations(self, agent: AgentConfig | None) -> int:
        if agent is None:
            return self.max_tool_iterations
        raw = agent.execution_limits.get("max_tool_iterations")
        if isinstance(raw, int) and raw > 0:
            return min(raw, 20)
        return self.max_tool_iterations

    def _build_routed_clients(
        self,
        *,
        workspace_id: str,
        project_id: str,
        user_id: str,
        agent: AgentConfig | None,
    ) -> tuple[LLMClient, LLMClient]:
        route = self.model_router.build_route(
            planner_model=agent.planner_model if agent is not None else None,
            generation_model=agent.generation_model if agent is not None else None,
            fallback_model=agent.fallback_model if agent is not None else None,
        )
        planner = self.model_router.planner_client(route)
        generation = self.model_router.generation_client(route)
        planner_instrumented = InstrumentedLLMClient(
            wrapped=planner,
            usage=self.usage,
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            run_id=None,
            provider=self.model_router.provider,
            model=route.planner_model,
            category="planner",
        )
        generation_instrumented = InstrumentedLLMClient(
            wrapped=generation,
            usage=self.usage,
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            run_id=None,
            provider=self.model_router.provider,
            model=route.generation_model,
            category="generation",
        )
        return planner_instrumented, generation_instrumented

    async def _store_memory_from_turn(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        agent: AgentConfig | None,
        user_text: str,
        assistant_text: str,
    ) -> None:
        summary = f"User: {user_text.strip()}\nAssistant: {assistant_text.strip()}"
        await self.memory.add_memory(
            session=self.session,
            request=MemoryCreateRequest(
                workspace_id=chat.workspace_id,
                project_id=chat.project_id,
                agent_id=agent.id if agent is not None else None,
                source_chat_id=chat.id,
                content=summary[:12000],
                metadata={"source": "chat_turn"},
            ),
            user=user,
        )

    def _sse_event(self, event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
