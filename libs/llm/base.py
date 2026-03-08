from collections.abc import AsyncIterator
from typing import Literal, Protocol, TypedDict


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClient(Protocol):
    async def complete(self, messages: list[LLMMessage]) -> str: ...

    def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]: ...
