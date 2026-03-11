from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import UsageRecord


def _utc_now() -> datetime:
    return datetime.now(UTC)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


@dataclass
class UsageService:
    session: AsyncSession
    requests_per_minute: int = 60
    estimated_cost_per_1k_tokens: float = 0.001

    async def enforce_workspace_rate_limit(self, *, workspace_id: str) -> None:
        window_start = _utc_now() - timedelta(minutes=1)
        result = await self.session.execute(
            select(func.coalesce(func.sum(UsageRecord.request_count), 0)).where(
                UsageRecord.workspace_id == workspace_id,
                UsageRecord.category == "request",
                UsageRecord.created_at >= window_start,
            )
        )
        total = int(result.scalar_one())
        if total >= self.requests_per_minute:
            raise PermissionError("Workspace rate limit exceeded for the last minute")

    async def record_request(
        self,
        *,
        workspace_id: str,
        project_id: str | None,
        user_id: str,
        run_id: str | None = None,
    ) -> None:
        row = UsageRecord(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            run_id=run_id,
            category="request",
            request_count=1,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            usage_metadata={},
        )
        self.session.add(row)
        await self.session.commit()

    async def record_llm_usage(
        self,
        *,
        workspace_id: str,
        project_id: str | None,
        user_id: str,
        run_id: str | None,
        provider: str | None,
        model: str | None,
        prompt_text: str,
        completion_text: str,
        category: str = "llm",
        metadata: dict[str, object] | None = None,
    ) -> None:
        prompt_tokens = estimate_tokens(prompt_text)
        completion_tokens = estimate_tokens(completion_text)
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1000.0) * self.estimated_cost_per_1k_tokens
        row = UsageRecord(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            run_id=run_id,
            category=category,
            provider=provider,
            model=model,
            request_count=0,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            usage_metadata=metadata or {},
        )
        self.session.add(row)
        await self.session.commit()

    async def summarize(
        self,
        *,
        workspace_id: str,
        project_id: str | None = None,
    ) -> dict[str, object]:
        filters = [UsageRecord.workspace_id == workspace_id]
        if project_id is not None:
            filters.append(UsageRecord.project_id == project_id)

        result = await self.session.execute(
            select(
                func.coalesce(func.sum(UsageRecord.request_count), 0),
                func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
                func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
                func.coalesce(func.sum(UsageRecord.total_tokens), 0),
                func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0.0),
            ).where(*filters)
        )
        request_count, prompt_tokens, completion_tokens, total_tokens, cost = (
            result.one()
        )
        return {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "request_count": int(request_count),
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "estimated_cost_usd": float(cost),
        }
