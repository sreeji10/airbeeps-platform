from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from libs.schemas.auth import AuthenticatedUser
from libs.schemas.rag import RetrievedChunk
from libs.tools.base import Tool, ToolContext, ToolResult
from libs.tools.registry import ToolRegistry
from services.memory.service import MemoryService
from services.rag.service import RagService


class DatasetSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    dataset_ids: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=5, ge=1, le=20)


class HttpRequestInput(BaseModel):
    method: str = Field(default="GET", min_length=3, max_length=10)
    url: str = Field(min_length=1, max_length=2000)
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    body: dict[str, object] | None = None
    timeout_seconds: float | None = Field(default=None, ge=0.5, le=30.0)


class MemorySearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=20)


@dataclass
class RuntimeToolsFactory:
    rag: RagService
    default_retrieval_top_k: int
    memory: MemoryService | None = None
    default_memory_top_k: int = 4
    http_timeout_seconds: float = 8.0

    def build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="dataset_search",
                description=(
                    "Semantic search over workspace datasets. Use this when user asks "
                    "questions that depend on uploaded files or project knowledge."
                ),
                input_model=DatasetSearchInput,
                handler=self._dataset_search_handler,
            )
        )
        registry.register(
            Tool(
                name="http_request",
                description=(
                    "Make an outbound HTTP request to a public API and return a compact response."
                ),
                input_model=HttpRequestInput,
                handler=self._http_request_handler,
            )
        )
        if self.memory is not None:
            registry.register(
                Tool(
                    name="memory_search",
                    description=(
                        "Semantic search over persistent agent memory entries "
                        "stored for this workspace/project."
                    ),
                    input_model=MemorySearchInput,
                    handler=self._memory_search_handler,
                )
            )
        return registry

    async def _dataset_search_handler(
        self,
        payload: BaseModel,
        context: ToolContext,
    ) -> ToolResult:
        request = cast(DatasetSearchInput, payload)
        session = cast(AsyncSession, context.session)
        selected_dataset_ids = request.dataset_ids or context.dataset_ids
        resolved_top_k = request.top_k or self.default_retrieval_top_k
        hits: list[RetrievedChunk] = await self.rag.retrieve(
            session=session,
            workspace_id=context.workspace_id,
            project_id=context.project_id,
            query=request.query,
            dataset_ids=selected_dataset_ids,
            top_k=resolved_top_k,
        )
        preview = "\n".join(
            f"[{index}] {chunk.content}\nCitation: {chunk.citation}"
            for index, chunk in enumerate(hits, start=1)
        )
        return ToolResult(
            content=preview or "No relevant dataset chunks found.",
            data={
                "matches": [chunk.model_dump() for chunk in hits],
                "count": len(hits),
            },
        )

    async def _http_request_handler(
        self,
        payload: BaseModel,
        context: ToolContext,
    ) -> ToolResult:
        del context
        request = cast(HttpRequestInput, payload)
        method = request.method.upper()
        timeout = request.timeout_seconds or self.http_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method=method,
                url=request.url,
                headers=request.headers,
                params=request.params,
                json=request.body,
            )

        try:
            parsed_json = response.json()
        except ValueError:
            parsed_json = None

        body_preview: str
        if parsed_json is not None:
            body_preview = str(parsed_json)[:3000]
        else:
            body_preview = response.text[:3000]

        return ToolResult(
            content=(
                f"HTTP {response.status_code} from {response.url}\n"
                f"Body preview:\n{body_preview}"
            ),
            data={
                "status_code": response.status_code,
                "url": str(response.url),
                "headers": dict(response.headers),
                "json": parsed_json if isinstance(parsed_json, (dict, list)) else None,
                "text": None if parsed_json is not None else response.text[:8000],
            },
        )

    async def _memory_search_handler(
        self,
        payload: BaseModel,
        context: ToolContext,
    ) -> ToolResult:
        if self.memory is None:
            return ToolResult(
                content="Memory service unavailable.", data={"matches": []}
            )
        request = cast(MemorySearchInput, payload)
        session = cast(AsyncSession, context.session)
        matches = await self.memory.search(
            session=session,
            workspace_id=context.workspace_id,
            project_id=context.project_id,
            query=request.query,
            top_k=request.top_k or self.default_memory_top_k,
            user=AuthenticatedUser(user_id=context.user_id),
        )
        content = "\n".join(
            f"[{index}] {item.content} (score={item.score:.3f})"
            for index, item in enumerate(matches, start=1)
        )
        return ToolResult(
            content=content or "No relevant memory entries found.",
            data={
                "matches": [
                    {
                        "id": item.id,
                        "content": item.content,
                        "score": item.score,
                        "metadata": item.metadata,
                        "created_at": item.created_at,
                    }
                    for item in matches
                ]
            },
        )
