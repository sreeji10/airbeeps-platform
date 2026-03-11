from collections.abc import AsyncIterator
from typing import Any

from libs.llm.base import LLMMessage
from libs.schemas.rag import RetrievedChunk
from services.runtime.executor import RuntimeExecutor
from services.runtime.planner import RuntimePlanner


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[list[LLMMessage]] = []

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.calls.append(messages)
        if self._responses:
            return self._responses.pop(0)
        return ""

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        self.calls.append(messages)
        for token in ["hello", " world"]:
            yield token


class FakeRetrievalTool:
    async def search(
        self,
        *,
        session: Any,
        workspace_id: str,
        project_id: str,
        query: str,
        dataset_ids: list[str],
        top_k: int,
    ) -> list[RetrievedChunk]:
        return []


def test_runtime_planner_parses_json_plan() -> None:
    llm = FakeLLM(
        [
            '{"goal":"Answer user","steps":[{"id":"s1","kind":"analyze",'
            '"description":"Inspect request"}]}'
        ]
    )
    planner = RuntimePlanner(llm=llm)

    plan = __import__("asyncio").run(
        planner.build_plan(
            user_message="Help me summarize this",
            context_messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert plan.goal == "Answer user"
    assert len(plan.steps) == 1
    assert plan.steps[0].id == "s1"


def test_runtime_planner_fallback_when_invalid_json() -> None:
    llm = FakeLLM(["not-json-output"])
    planner = RuntimePlanner(llm=llm)

    plan = __import__("asyncio").run(
        planner.build_plan(
            user_message="Tell me a joke",
            context_messages=[{"role": "user", "content": "hi"}],
        )
    )

    assert len(plan.steps) == 3
    assert plan.steps[-1].kind == "respond"


def test_runtime_executor_builds_final_messages() -> None:
    llm = FakeLLM(["step-a", "step-b"])
    planner = RuntimePlanner(llm=llm)
    plan = __import__("asyncio").run(
        planner.build_plan(
            user_message="Explain this architecture",
            context_messages=[{"role": "user", "content": "question"}],
        )
    )

    executor = RuntimeExecutor(
        llm=llm,
        retrieval_tool=FakeRetrievalTool(),  # type: ignore[arg-type]
    )
    prepared = __import__("asyncio").run(
        executor.prepare(
            session=object(),  # type: ignore[arg-type]
            workspace_id="w1",
            project_id="p1",
            dataset_ids=[],
            plan=plan,
            context_messages=[{"role": "system", "content": "sys"}],
            user_message="Explain this architecture",
        )
    )

    assert prepared.intermediate_results
    assert prepared.final_messages[-1]["role"] == "user"
