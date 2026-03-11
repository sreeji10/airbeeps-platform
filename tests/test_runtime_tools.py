import asyncio
from collections.abc import AsyncIterator

from libs.llm.base import LLMMessage
from libs.schemas.runtime import ExecutionPlan, ExecutionPlanStep
from libs.tools.base import Tool, ToolContext, ToolResult
from libs.tools.registry import ToolRegistry
from pydantic import BaseModel, Field
from services.runtime.executor import RuntimeExecutor


class ScriptedLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses

    async def complete(self, messages: list[LLMMessage]) -> str:
        del messages
        if self._responses:
            return self._responses.pop(0)
        return '{"action":"final","response":"done"}'

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        del messages
        if False:
            yield ""


class EchoInput(BaseModel):
    text: str = Field(default="", max_length=200)


async def _echo_handler(payload: BaseModel, context: ToolContext) -> ToolResult:
    del context
    value = EchoInput.model_validate(payload).text
    return ToolResult(content=f"echo:{value}", data={"value": value})


def _build_tools() -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(
        Tool(
            name="echo_tool",
            description="Echo text for testing.",
            input_model=EchoInput,
            handler=_echo_handler,
        )
    )
    return tools


def test_runtime_reason_act_loop_executes_tool_and_finishes() -> None:
    llm = ScriptedLLM(
        [
            '{"action":"tool","tool_name":"echo_tool","tool_input":{"text":"ping"}}',
            '{"action":"final","response":"Tool result consumed"}',
        ]
    )
    executor = RuntimeExecutor(llm=llm, tools=_build_tools(), max_tool_iterations=3)
    plan = ExecutionPlan(
        goal="answer",
        steps=[
            ExecutionPlanStep(id="s1", kind="reason", description="reason with tools")
        ],
    )

    prepared = asyncio.run(
        executor.prepare(
            session=object(),  # type: ignore[arg-type]
            workspace_id="w1",
            project_id="p1",
            user_id="u1",
            dataset_ids=[],
            plan=plan,
            context_messages=[{"role": "user", "content": "use a tool"}],
            user_message="use a tool",
        )
    )

    assert prepared.tool_calls
    assert prepared.tool_calls[0]["tool_name"] == "echo_tool"
    assert prepared.intermediate_results[0]["result"] == "Tool result consumed"
