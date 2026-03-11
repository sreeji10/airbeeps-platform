from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class ToolContext:
    workspace_id: str
    project_id: str
    user_id: str
    dataset_ids: list[str]
    session: Any


@dataclass(frozen=True)
class ToolResult:
    content: str
    data: dict[str, object]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, object]


ToolHandler = Callable[[BaseModel, ToolContext], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
        )

    async def execute(
        self, raw_input: dict[str, object], context: ToolContext
    ) -> ToolResult:
        try:
            validated = self.input_model.model_validate(raw_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid input for tool '{self.name}': {exc}") from exc
        return await self.handler(validated, context)
