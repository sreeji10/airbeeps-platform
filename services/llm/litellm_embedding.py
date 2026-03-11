from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, cast

from litellm import aembedding

from libs.embeddings.base import EmbeddingClient


@dataclass
class LiteLLMEmbeddingClient(EmbeddingClient):
    model: str
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    fallback_dimensions: int = 256

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await aembedding(
                model=self.model,
                input=texts,
                api_key=self.api_key,
                base_url=self.base_url,
                custom_llm_provider=self.provider,
            )
            data = cast(list[Any], response.data)
            vectors: list[list[float]] = []
            for row in data:
                vector = getattr(row, "embedding", None)
                if isinstance(vector, list):
                    vectors.append([float(x) for x in vector])
                else:
                    vectors.append([])
            if all(vectors):
                return vectors
        except Exception:
            pass

        return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> list[float]:
        values = [0.0] * self.fallback_dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.fallback_dimensions
            sign = -1.0 if digest[4] % 2 else 1.0
            values[index] += sign

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return values
        return [value / norm for value in values]
