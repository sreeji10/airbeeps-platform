from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from libs.llm.base import LLMMessage
from libs.schemas.rag import RetrievedChunk
from libs.schemas.runtime import ExecutionPlan


class RuntimeEvent(TypedDict):
    type: Literal["status", "token", "completed", "error"]
    data: dict[str, object]


@dataclass
class RuntimeExecutionResult:
    plan_id: str
    run_id: str
    run_status: str
    response: str
    plan: ExecutionPlan
    intermediate_results: list[dict[str, str]]
    tool_calls: list[dict[str, object]]


@dataclass
class RuntimePreparationResult:
    plan: ExecutionPlan
    intermediate_results: list[dict[str, str]]
    final_messages: list[LLMMessage]
    retrieved_chunks: list[RetrievedChunk]
    tool_calls: list[dict[str, object]]
