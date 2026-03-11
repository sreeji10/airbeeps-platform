from __future__ import annotations

from dataclasses import dataclass

from libs.llm.base import LLMClient
from services.llm.litellm_client import LiteLLMClient


@dataclass(frozen=True)
class ModelRoute:
    planner_model: str
    generation_model: str
    fallback_model: str | None = None


@dataclass
class ModelRouter:
    default_model: str
    provider: str | None
    api_key: str | None
    base_url: str | None
    temperature: float

    def build_route(
        self,
        *,
        planner_model: str | None = None,
        generation_model: str | None = None,
        fallback_model: str | None = None,
    ) -> ModelRoute:
        return ModelRoute(
            planner_model=planner_model or self.default_model,
            generation_model=generation_model or self.default_model,
            fallback_model=fallback_model,
        )

    def planner_client(self, route: ModelRoute) -> LLMClient:
        return LiteLLMClient(
            model=route.planner_model,
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            fallback_model=route.fallback_model,
        )

    def generation_client(self, route: ModelRoute) -> LLMClient:
        return LiteLLMClient(
            model=route.generation_model,
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            fallback_model=route.fallback_model,
        )
