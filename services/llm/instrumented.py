from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from libs.llm.base import LLMClient, LLMMessage
from services.usage.service import UsageService


@dataclass
class InstrumentedLLMClient:
    wrapped: LLMClient
    usage: UsageService
    workspace_id: str
    project_id: str | None
    user_id: str
    run_id: str | None
    provider: str | None
    model: str | None
    category: str

    async def complete(self, messages: list[LLMMessage]) -> str:
        prompt_text = self._flatten_messages(messages)
        response = await self.wrapped.complete(messages)
        await self.usage.record_llm_usage(
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            user_id=self.user_id,
            run_id=self.run_id,
            provider=self.provider,
            model=self.model,
            prompt_text=prompt_text,
            completion_text=response,
            category=self.category,
        )
        return response

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        prompt_text = self._flatten_messages(messages)
        chunks: list[str] = []
        async for token in self.wrapped.stream(messages):
            chunks.append(token)
            yield token
        await self.usage.record_llm_usage(
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            user_id=self.user_id,
            run_id=self.run_id,
            provider=self.provider,
            model=self.model,
            prompt_text=prompt_text,
            completion_text="".join(chunks),
            category=self.category,
        )

    def _flatten_messages(self, messages: list[LLMMessage]) -> str:
        return "\n".join(
            f"[{message['role']}] {message['content']}" for message in messages
        )
