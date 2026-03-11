from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import Chat, Plan, Run
from libs.llm.base import LLMMessage
from libs.schemas.auth import AuthenticatedUser
from services.runtime.executor import RuntimeExecutor
from services.runtime.planner import RuntimePlanner
from services.runtime.types import RuntimeEvent, RuntimeExecutionResult


class RuntimeService(Protocol):
    async def execute_turn(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        user_message: str,
        context_messages: list[LLMMessage],
        dataset_ids: list[str],
    ) -> RuntimeExecutionResult: ...

    async def stream_turn(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        user_message: str,
        context_messages: list[LLMMessage],
        dataset_ids: list[str],
    ) -> AsyncIterator[RuntimeEvent]: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class RuntimeServiceImpl:
    session: AsyncSession
    planner: RuntimePlanner
    executor: RuntimeExecutor

    async def execute_turn(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        user_message: str,
        context_messages: list[LLMMessage],
        dataset_ids: list[str],
    ) -> RuntimeExecutionResult:
        plan_model = await self.planner.build_plan(
            user_message=user_message,
            context_messages=context_messages,
        )
        plan = await self._create_plan(
            chat=chat,
            user=user,
            plan_payload={
                **plan_model.model_dump(),
                "dataset_ids": dataset_ids,
            },
        )
        run = await self._create_run(
            chat=chat,
            plan=plan,
            prompt=user_message,
            dataset_ids=dataset_ids,
        )
        await self._set_run_state(run=run, plan=plan, status="running")

        async def on_node_event(
            event_type: str,
            node: str,
            data: dict[str, object],
        ) -> None:
            await self._append_run_event(
                run,
                {
                    "type": event_type,
                    "node": node,
                    "data": data,
                    "at": _utc_now().isoformat(),
                },
            )

        try:
            preparation = await self.executor.prepare(
                session=self.session,
                workspace_id=chat.workspace_id,
                project_id=chat.project_id,
                dataset_ids=dataset_ids,
                plan=plan_model,
                context_messages=context_messages,
                user_message=user_message,
                on_node_event=on_node_event,
            )
            response_text = await self.executor.complete(preparation.final_messages)
            await self._complete_run(
                run=run,
                plan=plan,
                output={
                    "response": response_text,
                    "plan": plan_model.model_dump(),
                    "dataset_ids": dataset_ids,
                    "retrieved_chunks": [
                        chunk.model_dump() for chunk in preparation.retrieved_chunks
                    ],
                    "intermediate_results": preparation.intermediate_results,
                },
            )
            return RuntimeExecutionResult(
                plan_id=plan.id,
                run_id=run.id,
                run_status=run.status,
                response=response_text,
                plan=plan_model,
                intermediate_results=preparation.intermediate_results,
            )
        except Exception as exc:
            await self._fail_run(run=run, plan=plan, error=str(exc))
            raise

    async def stream_turn(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        user_message: str,
        context_messages: list[LLMMessage],
        dataset_ids: list[str],
    ) -> AsyncIterator[RuntimeEvent]:
        plan_model = await self.planner.build_plan(
            user_message=user_message,
            context_messages=context_messages,
        )
        plan = await self._create_plan(
            chat=chat,
            user=user,
            plan_payload={
                **plan_model.model_dump(),
                "dataset_ids": dataset_ids,
            },
        )
        run = await self._create_run(
            chat=chat,
            plan=plan,
            prompt=user_message,
            dataset_ids=dataset_ids,
        )
        await self._set_run_state(run=run, plan=plan, status="running")

        event_queue: list[RuntimeEvent] = []
        buffered_tokens: list[str] = []

        async def on_node_event(
            event_type: str,
            node: str,
            data: dict[str, object],
        ) -> None:
            persisted_event: dict[str, object] = {
                "type": event_type,
                "node": node,
                "data": data,
                "at": _utc_now().isoformat(),
            }
            await self._append_run_event(run, persisted_event)
            event_queue.append({"type": "status", "data": persisted_event})

        try:
            preparation = await self.executor.prepare(
                session=self.session,
                workspace_id=chat.workspace_id,
                project_id=chat.project_id,
                dataset_ids=dataset_ids,
                plan=plan_model,
                context_messages=context_messages,
                user_message=user_message,
                on_node_event=on_node_event,
            )

            while event_queue:
                yield event_queue.pop(0)

            async for token in self.executor.llm.stream(preparation.final_messages):
                buffered_tokens.append(token)
                yield {"type": "token", "data": {"token": token, "run_id": run.id}}

            response_text = "".join(buffered_tokens)
            await self._complete_run(
                run=run,
                plan=plan,
                output={
                    "response": response_text,
                    "plan": plan_model.model_dump(),
                    "dataset_ids": dataset_ids,
                    "retrieved_chunks": [
                        chunk.model_dump() for chunk in preparation.retrieved_chunks
                    ],
                    "intermediate_results": preparation.intermediate_results,
                },
            )
            yield {
                "type": "completed",
                "data": {
                    "plan_id": plan.id,
                    "run_id": run.id,
                    "status": run.status,
                    "response": response_text,
                },
            }
        except Exception as exc:
            await self._fail_run(run=run, plan=plan, error=str(exc))
            yield {"type": "error", "data": {"message": str(exc), "run_id": run.id}}

    async def _create_plan(
        self,
        *,
        chat: Chat,
        user: AuthenticatedUser,
        plan_payload: dict[str, object],
    ) -> Plan:
        plan = Plan(
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            chat_id=chat.id,
            status="created",
            payload=plan_payload,
            created_by=user.user_id,
        )
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def _create_run(
        self,
        *,
        chat: Chat,
        plan: Plan,
        prompt: str,
        dataset_ids: list[str],
    ) -> Run:
        run = Run(
            workspace_id=chat.workspace_id,
            project_id=chat.project_id,
            plan_id=plan.id,
            status="created",
            input_payload={
                "chat_id": chat.id,
                "prompt": prompt,
                "dataset_ids": dataset_ids,
            },
            output_payload={"events": []},
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

    async def _append_run_event(self, run: Run, event: dict[str, object]) -> None:
        events_raw = run.output_payload.get("events", [])
        events: list[dict[str, object]] = []
        if isinstance(events_raw, list):
            for item in events_raw:
                if isinstance(item, dict):
                    events.append(cast(dict[str, object], item))
        events.append(event)
        run.output_payload = {**run.output_payload, "events": events}
        self.session.add(run)
        await self.session.commit()

    async def _complete_run(
        self, *, run: Run, plan: Plan, output: dict[str, object]
    ) -> None:
        run.status = "completed"
        run.output_payload = {**run.output_payload, **output}
        run.completed_at = _utc_now()
        plan.status = "completed"
        self.session.add(run)
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(run)

    async def _fail_run(self, *, run: Run, plan: Plan, error: str) -> None:
        run.status = "failed"
        run.output_payload = {**run.output_payload, "error": error}
        run.completed_at = _utc_now()
        plan.status = "failed"
        self.session.add(run)
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(run)
