import asyncio
from typing import Any

from libs.llm.base import LLMMessage
from libs.schemas.rag import RetrievedChunk
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep
from services.runtime.executor import RuntimeExecutor


class FakeLLM:
    async def complete(self, messages: list[LLMMessage]) -> str:
        return "analysis"

    async def stream(self, messages: list[LLMMessage]):
        if False:
            yield ""


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
        return [
            RetrievedChunk(
                dataset_id=dataset_ids[0] if dataset_ids else "d1",
                chunk_id="c1",
                score=0.9,
                content="retrieved context",
                citation="doc#1",
            )
        ]


def test_executor_injects_retrieval_context() -> None:
    executor = RuntimeExecutor(
        llm=FakeLLM(),
        retrieval_tool=FakeRetrievalTool(),  # type: ignore[arg-type]
        retrieval_top_k=3,
    )
    plan = ExecutionPlan(
        goal="answer",
        steps=[
            ExecutionPlanStep(
                id="s1",
                kind="retrieve_context",
                description="retrieve",
            ),
            ExecutionPlanStep(
                id="s2",
                kind="analyze",
                description="analyze",
            ),
        ],
    )

    prepared = asyncio.run(
        executor.prepare(
            session=object(),  # type: ignore[arg-type]
            workspace_id="w1",
            project_id="p1",
            dataset_ids=["d1"],
            plan=plan,
            context_messages=[{"role": "user", "content": "What is this?"}],
            user_message="What is this?",
        )
    )

    assert prepared.retrieved_chunks
    final_prompt = prepared.final_messages[-1]["content"]
    assert "retrieved context" in final_prompt
