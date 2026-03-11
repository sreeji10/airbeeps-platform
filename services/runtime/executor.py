from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.rag import RetrievedChunk
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep
from libs.tools.base import ToolContext
from libs.tools.registry import ToolCallResult, ToolRegistry
from services.runtime.types import RuntimePreparationResult


class RuntimeGraphState(TypedDict):
    context_messages: list[LLMMessage]
    user_message: str
    goal: str
    intermediate_results: list[dict[str, str]]
    final_messages: list[LLMMessage]
    retrieved_chunks: list[RetrievedChunk]
    tool_calls: list[dict[str, object]]


NodeCallback = Callable[[str, str, dict[str, object]], Awaitable[None]]


@dataclass
class RuntimeExecutor:
    llm: LLMClient
    tools: ToolRegistry
    retrieval_top_k: int = 5
    max_tool_iterations: int = 4

    async def prepare(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        user_id: str,
        dataset_ids: list[str],
        plan: ExecutionPlan,
        context_messages: list[LLMMessage],
        user_message: str,
        on_node_event: NodeCallback | None = None,
    ) -> RuntimePreparationResult:
        graph = self._build_graph(
            session=session,
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            dataset_ids=dataset_ids,
            steps=plan.steps,
            on_node_event=on_node_event,
        )
        initial_state: RuntimeGraphState = {
            "context_messages": context_messages,
            "user_message": user_message,
            "goal": plan.goal,
            "intermediate_results": [],
            "final_messages": [],
            "retrieved_chunks": [],
            "tool_calls": [],
        }
        result = cast(RuntimeGraphState, await graph.ainvoke(initial_state))
        return RuntimePreparationResult(
            plan=plan,
            intermediate_results=result.get("intermediate_results", []),
            final_messages=result.get("final_messages", []),
            retrieved_chunks=result.get("retrieved_chunks", []),
            tool_calls=result.get("tool_calls", []),
        )

    async def complete(self, final_messages: list[LLMMessage]) -> str:
        return await self.llm.complete(final_messages)

    def _build_graph(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        user_id: str,
        dataset_ids: list[str],
        steps: list[ExecutionPlanStep],
        on_node_event: NodeCallback | None,
    ) -> Any:
        graph: StateGraph[RuntimeGraphState] = StateGraph(RuntimeGraphState)

        previous_node = START
        for step in steps:
            node_name = f"plan_{step.id}"
            action = cast(
                Any,
                self._make_step_node(
                    session=session,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    user_id=user_id,
                    dataset_ids=dataset_ids,
                    step=step,
                    on_node_event=on_node_event,
                ),
            )
            graph.add_node(node_name, action)
            graph.add_edge(previous_node, node_name)
            previous_node = node_name

        graph.add_node(
            "compose_final_messages", cast(Any, self._compose_final_messages)
        )
        graph.add_edge(previous_node, "compose_final_messages")
        graph.add_edge("compose_final_messages", END)
        return graph.compile()

    def _make_step_node(
        self,
        *,
        session: AsyncSession,
        workspace_id: str,
        project_id: str,
        user_id: str,
        dataset_ids: list[str],
        step: ExecutionPlanStep,
        on_node_event: NodeCallback | None,
    ) -> Callable[[RuntimeGraphState], Awaitable[dict[str, object]]]:
        async def run_step(state: RuntimeGraphState) -> dict[str, object]:
            node_name = f"plan_{step.id}"
            if on_node_event is not None:
                await on_node_event(
                    "started",
                    node_name,
                    {
                        "step_id": step.id,
                        "kind": step.kind,
                        "description": step.description,
                    },
                )

            intermediate_results = list(state["intermediate_results"])
            retrieved_chunks = list(state["retrieved_chunks"])
            tool_calls = list(state["tool_calls"])
            tool_context = ToolContext(
                workspace_id=workspace_id,
                project_id=project_id,
                user_id=user_id,
                dataset_ids=dataset_ids,
                session=session,
            )

            if step.kind == "retrieve_context":
                retrieval = await self.tools.execute(
                    name="dataset_search",
                    payload={
                        "query": state["user_message"],
                        "dataset_ids": dataset_ids,
                        "top_k": self.retrieval_top_k,
                    },
                    context=tool_context,
                )
                retrieved_chunks = self._extract_retrieved_chunks(retrieval)
                tool_calls.append(
                    {
                        "step_id": step.id,
                        "tool_name": retrieval.tool_name,
                        "ok": retrieval.ok,
                        "error": retrieval.error,
                        "data": retrieval.data,
                    }
                )
                step_result = (
                    f"retrieved {len(retrieved_chunks)} chunks from "
                    f"{len({h.dataset_id for h in retrieved_chunks})} datasets"
                    if retrieved_chunks
                    else "no relevant chunks found"
                )
            else:
                step_result = await self._run_reason_act_loop(
                    step=step,
                    state=state,
                    tool_context=tool_context,
                    tool_calls=tool_calls,
                    on_node_event=on_node_event,
                )

            intermediate_results.append(
                {
                    "step_id": step.id,
                    "kind": step.kind,
                    "description": step.description,
                    "result": step_result,
                }
            )

            if on_node_event is not None:
                await on_node_event(
                    "completed",
                    node_name,
                    {
                        "step_id": step.id,
                        "result": step_result,
                        "retrieved_chunks": len(retrieved_chunks),
                        "tool_calls": len(tool_calls),
                    },
                )

            return {
                "intermediate_results": intermediate_results,
                "retrieved_chunks": retrieved_chunks,
                "tool_calls": tool_calls,
            }

        return run_step

    async def _run_reason_act_loop(
        self,
        *,
        step: ExecutionPlanStep,
        state: RuntimeGraphState,
        tool_context: ToolContext,
        tool_calls: list[dict[str, object]],
        on_node_event: NodeCallback | None,
    ) -> str:
        observations: list[str] = []
        final_response = ""
        for iteration in range(1, self.max_tool_iterations + 1):
            loop_messages: list[LLMMessage] = [*state["context_messages"]]
            loop_messages.append(
                {
                    "role": "system",
                    "content": self._tool_loop_system_prompt(),
                }
            )
            loop_messages.append(
                {
                    "role": "user",
                    "content": self._tool_loop_user_prompt(
                        step=step,
                        state=state,
                        observations=observations,
                    ),
                }
            )

            decision_raw = await self.llm.complete(loop_messages)
            decision = self._parse_decision(decision_raw)
            if decision is None:
                return decision_raw

            if decision["action"] == "final":
                final_response = str(decision.get("response", "")).strip()
                if final_response:
                    return final_response
                return decision_raw

            tool_name = str(decision.get("tool_name", "")).strip()
            tool_input = decision.get("tool_input", {})
            if not isinstance(tool_input, dict):
                tool_input = {}

            if on_node_event is not None:
                await on_node_event(
                    "tool_started",
                    f"step_{step.id}",
                    {
                        "step_id": step.id,
                        "iteration": iteration,
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                    },
                )

            result = await self.tools.execute(
                name=tool_name,
                payload=cast(dict[str, object], tool_input),
                context=tool_context,
            )
            tool_event = self._tool_result_to_event(
                step.id, iteration, result, tool_input
            )
            tool_calls.append(tool_event)
            observations.append(self._format_tool_observation(result, tool_input))

            if on_node_event is not None:
                await on_node_event(
                    "tool_completed",
                    f"step_{step.id}",
                    {
                        "step_id": step.id,
                        "iteration": iteration,
                        "tool_name": tool_name,
                        "ok": result.ok,
                        "error": result.error,
                    },
                )

        if final_response:
            return final_response
        if observations:
            return observations[-1]
        return "No result generated."

    def _tool_loop_system_prompt(self) -> str:
        return (
            "You are the reasoning engine inside Airbeeps runtime.\n"
            "You can either call a tool or provide a final step result.\n"
            "Return ONLY valid JSON with this schema:\n"
            "{"
            '"action":"tool|final",'
            '"tool_name":"string when action=tool",'
            '"tool_input":{...} when action=tool,'
            '"response":"string when action=final"'
            "}\n"
            "If tool output is enough, return action=final."
        )

    def _tool_loop_user_prompt(
        self,
        *,
        step: ExecutionPlanStep,
        state: RuntimeGraphState,
        observations: list[str],
    ) -> str:
        intermediate_text = "\n".join(
            f"- {item['step_id']} ({item['kind']}): {item['result']}"
            for item in state["intermediate_results"]
        )
        retrieval_text = "\n\n".join(
            f"[{index}] {chunk.content}\nCitation: {chunk.citation}"
            for index, chunk in enumerate(state["retrieved_chunks"], start=1)
        )
        observation_text = "\n\n".join(observations)
        tools_text = self._tools_catalog_text()
        return (
            f"Goal: {state['goal']}\n"
            f"Current step: {step.id} ({step.kind})\n"
            f"Step description: {step.description}\n"
            f"User message: {state['user_message']}\n\n"
            "Available tools:\n"
            f"{tools_text}\n\n"
            "Execution notes so far:\n"
            f"{intermediate_text or '- none'}\n\n"
            "Retrieved context:\n"
            f"{retrieval_text or '- none'}\n\n"
            "Tool observations so far:\n"
            f"{observation_text or '- none'}"
        )

    def _tools_catalog_text(self) -> str:
        specs = self.tools.list_specs()
        if not specs:
            return "- none"
        return "\n".join(
            (
                f"- name: {spec.name}\n"
                f"  description: {spec.description}\n"
                f"  input_schema: {json.dumps(spec.input_schema)}"
            )
            for spec in specs
        )

    def _parse_decision(self, raw: str) -> dict[str, object] | None:
        payload = self._extract_json(raw)
        if payload is None:
            return None
        action = str(payload.get("action", "")).strip().lower()
        if action not in {"tool", "final"}:
            return None
        return payload

    def _extract_json(self, text: str) -> dict[str, object] | None:
        if not text.strip():
            return None
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return cast(dict[str, object], loaded)
        except json.JSONDecodeError:
            pass

        block_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if block_match:
            try:
                loaded = json.loads(block_match.group(1))
                if isinstance(loaded, dict):
                    return cast(dict[str, object], loaded)
            except json.JSONDecodeError:
                return None

        json_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if json_match:
            try:
                loaded = json.loads(json_match.group(1))
                if isinstance(loaded, dict):
                    return cast(dict[str, object], loaded)
            except json.JSONDecodeError:
                return None
        return None

    def _tool_result_to_event(
        self,
        step_id: str,
        iteration: int,
        result: ToolCallResult,
        tool_input: dict[str, object],
    ) -> dict[str, object]:
        return {
            "step_id": step_id,
            "iteration": iteration,
            "tool_name": result.tool_name,
            "tool_input": tool_input,
            "ok": result.ok,
            "content": result.content,
            "data": result.data,
            "error": result.error,
        }

    def _format_tool_observation(
        self,
        result: ToolCallResult,
        tool_input: dict[str, object],
    ) -> str:
        if result.ok:
            return (
                f"Tool {result.tool_name} called with {json.dumps(tool_input)}\n"
                f"Result: {result.content}"
            )
        return (
            f"Tool {result.tool_name} called with {json.dumps(tool_input)}\n"
            f"Error: {result.error or 'unknown error'}"
        )

    def _extract_retrieved_chunks(
        self, retrieval: ToolCallResult
    ) -> list[RetrievedChunk]:
        if not retrieval.ok:
            return []
        matches = retrieval.data.get("matches", [])
        if not isinstance(matches, list):
            return []
        chunks: list[RetrievedChunk] = []
        for item in matches:
            if not isinstance(item, dict):
                continue
            try:
                chunks.append(RetrievedChunk.model_validate(item))
            except Exception:
                continue
        return chunks

    async def _compose_final_messages(
        self, state: RuntimeGraphState
    ) -> dict[str, object]:
        intermediate_text = "\n".join(
            f"- {item['step_id']} ({item['kind']}): {item['result']}"
            for item in state["intermediate_results"]
        )
        retrieval_text = "\n\n".join(
            f"[{index}] {chunk.content}\nCitation: {chunk.citation}"
            for index, chunk in enumerate(state["retrieved_chunks"], start=1)
        )
        tool_text = "\n\n".join(
            (
                f"[{index}] {call.get('tool_name')}"
                f" | ok={call.get('ok')}"
                f" | input={call.get('tool_input')}"
                f"\noutput={call.get('content') or call.get('error')}"
            )
            for index, call in enumerate(state["tool_calls"], start=1)
        )

        final_messages: list[LLMMessage] = [*state["context_messages"]]
        final_messages.append(
            {
                "role": "system",
                "content": (
                    "You are Airbeeps runtime. Produce the final user-facing response using the "
                    "execution notes and retrieved context. "
                    "If retrieval context is present, ground the answer in it and mention citations."
                ),
            }
        )
        final_messages.append(
            {
                "role": "user",
                "content": (
                    f"Goal: {state['goal']}\n"
                    f"User message: {state['user_message']}\n"
                    "Execution notes:\n"
                    f"{intermediate_text or '- no intermediate notes'}\n\n"
                    "Tool call logs:\n"
                    f"{tool_text or '- no tool calls'}\n\n"
                    "Retrieved context:\n"
                    f"{retrieval_text or '- no retrieval context'}"
                ),
            }
        )
        return {"final_messages": final_messages}
