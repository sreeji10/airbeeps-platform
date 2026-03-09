from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep
from services.runtime.types import RuntimePreparationResult


class RuntimeGraphState(TypedDict):
    context_messages: list[LLMMessage]
    user_message: str
    goal: str
    intermediate_results: list[dict[str, str]]
    final_messages: list[LLMMessage]


NodeCallback = Callable[[str, str, dict[str, object]], Awaitable[None]]


@dataclass
class RuntimeExecutor:
    llm: LLMClient

    async def prepare(
        self,
        *,
        plan: ExecutionPlan,
        context_messages: list[LLMMessage],
        user_message: str,
        on_node_event: NodeCallback | None = None,
    ) -> RuntimePreparationResult:
        graph = self._build_graph(plan.steps, on_node_event)
        initial_state: RuntimeGraphState = {
            "context_messages": context_messages,
            "user_message": user_message,
            "goal": plan.goal,
            "intermediate_results": [],
            "final_messages": [],
        }
        result = cast(RuntimeGraphState, await graph.ainvoke(initial_state))
        return RuntimePreparationResult(
            plan=plan,
            intermediate_results=result.get("intermediate_results", []),
            final_messages=result.get("final_messages", []),
        )

    async def complete(self, final_messages: list[LLMMessage]) -> str:
        return await self.llm.complete(final_messages)

    def _build_graph(
        self,
        steps: list[ExecutionPlanStep],
        on_node_event: NodeCallback | None,
    ) -> Any:
        graph: StateGraph[RuntimeGraphState] = StateGraph(RuntimeGraphState)

        previous_node = START
        for step in steps:
            node_name = f"plan_{step.id}"
            action = cast(Any, self._make_step_node(step, on_node_event))
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

            step_messages: list[LLMMessage] = list(state["context_messages"])
            step_messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are executing a step inside an agent runtime. "
                        "Return a short factual result for this step."
                    ),
                }
            )
            step_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Goal: {state['goal']}\n"
                        f"Current step: {step.id} ({step.kind})\n"
                        f"Step description: {step.description}\n"
                        f"User message: {state['user_message']}"
                    ),
                }
            )
            step_result = await self.llm.complete(step_messages)

            intermediate_results = [
                *state["intermediate_results"],
                {
                    "step_id": step.id,
                    "kind": step.kind,
                    "description": step.description,
                    "result": step_result,
                },
            ]

            if on_node_event is not None:
                await on_node_event(
                    "completed",
                    node_name,
                    {"step_id": step.id, "result": step_result},
                )

            return {"intermediate_results": intermediate_results}

        return run_step

    async def _compose_final_messages(
        self, state: RuntimeGraphState
    ) -> dict[str, object]:
        intermediate_text = "\n".join(
            f"- {item['step_id']} ({item['kind']}): {item['result']}"
            for item in state["intermediate_results"]
        )

        final_messages: list[LLMMessage] = [*state["context_messages"]]
        final_messages.append(
            {
                "role": "system",
                "content": (
                    "You are Airbeeps runtime. Produce the final user-facing response using the "
                    "execution notes while staying concise and correct."
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
                    f"{intermediate_text or '- no intermediate notes'}"
                ),
            }
        )
        return {"final_messages": final_messages}
