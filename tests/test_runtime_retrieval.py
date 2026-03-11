import asyncio
from typing import Any

from libs.llm.base import LLMMessage
from libs.schemas.rag import RetrievedChunk
from libs.tools.base import Tool, ToolContext, ToolResult
from libs.tools.registry import ToolRegistry
from pydantic import BaseModel, Field
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep
from services.runtime.executor import RuntimeExecutor


class FakeLLM:
    async def complete(self, messages: list[LLMMessage]) -> str:
        return "analysis"

    async def stream(self, messages: list[LLMMessage]):
        if False:
            yield ""


class DatasetSearchInput(BaseModel):
    query: str
    dataset_ids: list[str] = Field(default_factory=list)
    top_k: int = 5


async def _dataset_search(payload: Any, context: ToolContext) -> ToolResult:
    request = DatasetSearchInput.model_validate(payload)
    chunk = RetrievedChunk(
        dataset_id=request.dataset_ids[0]
        if request.dataset_ids
        else context.dataset_ids[0],
        chunk_id="c1",
        score=0.9,
        content="retrieved context",
        citation="doc#1",
    )
    return ToolResult(content="ok", data={"matches": [chunk.model_dump()], "count": 1})


def _tools() -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(
        Tool(
            name="dataset_search",
            description="search",
            input_model=DatasetSearchInput,
            handler=_dataset_search,
        )
    )
    return tools


def test_executor_injects_retrieval_context() -> None:
    executor = RuntimeExecutor(
        llm=FakeLLM(),
        tools=_tools(),
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
            user_id="u1",
            dataset_ids=["d1"],
            plan=plan,
            context_messages=[{"role": "user", "content": "What is this?"}],
            user_message="What is this?",
        )
    )

    assert prepared.retrieved_chunks
    final_prompt = prepared.final_messages[-1]["content"]
    assert "retrieved context" in final_prompt
