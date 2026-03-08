from dataclasses import dataclass
from typing import Protocol


class Tool(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    def execute(self, payload: str) -> str: ...


@dataclass(frozen=True)
class EchoTool:
    name: str = "echo"
    description: str = "Returns the same payload for connectivity checks."

    def execute(self, payload: str) -> str:
        return payload
