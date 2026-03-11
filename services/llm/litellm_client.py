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
    fallback_model: str | None = None

    async def complete(self, messages: list[LLMMessage]) -> str:
        response = await self._completion_with_fallback(messages=messages, stream=False)
        choices = cast(list[Any], response.choices)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "")
        return content if isinstance(content, str) else ""

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        response_stream = await self._completion_with_fallback(
            messages=messages, stream=True
        )
        async for chunk in response_stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            token = getattr(delta, "content", "")
            if isinstance(token, str) and token:
                yield token

    async def _completion_with_fallback(
        self,
        *,
        messages: list[LLMMessage],
        stream: bool,
    ) -> Any:
        try:
            return await acompletion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                base_url=self.base_url,
                custom_llm_provider=self.provider,
                temperature=self.temperature,
                stream=stream,
            )
        except Exception:
            if not self.fallback_model:
                raise
            return await acompletion(
                model=self.fallback_model,
                messages=messages,
                api_key=self.api_key,
                base_url=self.base_url,
                custom_llm_provider=self.provider,
                temperature=self.temperature,
                stream=stream,
            )
