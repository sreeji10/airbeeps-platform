from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

from litellm import acompletion

from libs.llm.base import LLMMessage


@dataclass
class LiteLLMClient:
    model: str
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2

    async def complete(self, messages: list[LLMMessage]) -> str:
        response = await acompletion(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            base_url=self.base_url,
            custom_llm_provider=self.provider,
            temperature=self.temperature,
            stream=False,
        )
        choices = cast(list[Any], response.choices)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "")
        return content if isinstance(content, str) else ""

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        response_stream = await acompletion(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            base_url=self.base_url,
            custom_llm_provider=self.provider,
            temperature=self.temperature,
            stream=True,
        )
        async for chunk in response_stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            token = getattr(delta, "content", "")
            if isinstance(token, str) and token:
                yield token
