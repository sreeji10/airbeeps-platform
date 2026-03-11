from __future__ import annotations

from dataclasses import dataclass, field

from libs.tools.base import Tool, ToolContext, ToolResult, ToolSpec


@dataclass(frozen=True)
class ToolCallResult:
    tool_name: str
    ok: bool
    content: str
    data: dict[str, object]
    error: str | None = None


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def filtered(self, enabled_names: list[str]) -> ToolRegistry:
        subset = ToolRegistry()
        allowed = set(enabled_names)
        for name, tool in self._tools.items():
            if name in allowed:
                subset.register(tool)
        return subset

    async def execute(
        self,
        *,
        name: str,
        payload: dict[str, object],
        context: ToolContext,
    ) -> ToolCallResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolCallResult(
                tool_name=name,
                ok=False,
                content="",
                data={},
                error=f"Tool '{name}' is not registered",
            )
        try:
            result: ToolResult = await tool.execute(payload, context)
            return ToolCallResult(
                tool_name=name,
                ok=True,
                content=result.content,
                data=result.data,
            )
        except Exception as exc:
            return ToolCallResult(
                tool_name=name,
                ok=False,
                content="",
                data={},
                error=str(exc),
            )
