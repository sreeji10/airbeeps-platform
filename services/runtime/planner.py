from __future__ import annotations

import json
import re
from dataclasses import dataclass

from libs.llm.base import LLMClient, LLMMessage
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep


@dataclass
class RuntimePlanner:
    llm: LLMClient

    async def build_plan(
        self,
        *,
        user_message: str,
        context_messages: list[LLMMessage],
    ) -> ExecutionPlan:
        planning_messages: list[LLMMessage] = [
            {
                "role": "system",
                "content": (
                    "You are a planning engine for an AI agent runtime. "
                    "Return only valid JSON with keys: goal, steps. "
                    "steps must be an array of objects with id, kind, description."
                ),
            },
            {
                "role": "user",
                "content": self._planner_prompt(
                    user_message=user_message,
                    context_messages=context_messages,
                ),
            },
        ]
        raw = await self.llm.complete(planning_messages)
        parsed = self._parse_plan(raw)
        if parsed is not None:
            return parsed
        return self._fallback_plan(user_message)

    def _planner_prompt(
        self,
        *,
        user_message: str,
        context_messages: list[LLMMessage],
    ) -> str:
        history = "\n".join(
            f"- {msg['role']}: {msg['content']}"
            for msg in context_messages[-6:]
            if msg["role"] in {"user", "assistant"}
        )
        return (
            "Create a concise machine-readable execution plan for this user request.\n"
            f"User request: {user_message}\n"
            f"Recent history:\n{history or '- none'}\n"
            "Use kinds from: retrieve_context, analyze, reason, respond."
        )

    def _parse_plan(self, raw: str) -> ExecutionPlan | None:
        payload = self._extract_json(raw)
        if payload is None:
            return None
        try:
            plan = ExecutionPlan.model_validate(payload)
        except Exception:
            return None

        deduped_steps: list[ExecutionPlanStep] = []
        seen: set[str] = set()
        for index, step in enumerate(plan.steps, start=1):
            step_id = step.id.strip() or f"step_{index}"
            if step_id in seen:
                step_id = f"step_{index}"
            seen.add(step_id)
            deduped_steps.append(step.model_copy(update={"id": step_id}))

        return ExecutionPlan(version=plan.version, goal=plan.goal, steps=deduped_steps)

    def _extract_json(self, text: str) -> dict[str, object] | None:
        if not text.strip():
            return None
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass

        block_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if block_match:
            try:
                loaded = json.loads(block_match.group(1))
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                return None

        json_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if json_match:
            try:
                loaded = json.loads(json_match.group(1))
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                return None
        return None

    def _fallback_plan(self, user_message: str) -> ExecutionPlan:
        trimmed = user_message.strip()
        goal = trimmed if len(trimmed) <= 250 else f"{trimmed[:247]}..."
        return ExecutionPlan(
            goal=goal,
            steps=[
                ExecutionPlanStep(
                    id="step_1",
                    kind="retrieve_context",
                    description="Gather relevant chat context and available metadata.",
                ),
                ExecutionPlanStep(
                    id="step_2",
                    kind="analyze",
                    description="Analyze user intent and constraints from the request.",
                ),
                ExecutionPlanStep(
                    id="step_3",
                    kind="respond",
                    description="Generate the final assistant response for the user.",
                ),
            ],
        )
