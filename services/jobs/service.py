from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import BackgroundJob
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.job import JobCreateRequest
from services.platform.service import PlatformService


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class JobService:
    session: AsyncSession

    async def enqueue(
        self,
        *,
        request: JobCreateRequest,
        user: AuthenticatedUser,
    ) -> BackgroundJob:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        job = BackgroundJob(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            kind=request.kind,
            status="queued",
            payload=request.payload,
            result={},
            max_attempts=request.max_attempts,
            created_by=user.user_id,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(
        self,
        *,
        job_id: str,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> BackgroundJob | None:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(BackgroundJob).where(
                BackgroundJob.id == job_id,
                BackgroundJob.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        *,
        workspace_id: str,
        project_id: str | None,
        user: AuthenticatedUser,
        status: str | None = None,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_desc: bool = True,
    ) -> list[BackgroundJob]:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id,
            user_id=user.user_id,
        )
        query = select(BackgroundJob).where(BackgroundJob.workspace_id == workspace_id)
        if project_id is not None:
            query = query.where(BackgroundJob.project_id == project_id)
        if status is not None:
            query = query.where(BackgroundJob.status == status)
        if kind is not None:
            query = query.where(BackgroundJob.kind == kind)
        query = (
            query.order_by(
                BackgroundJob.created_at.desc()
                if sort_desc
                else BackgroundJob.created_at.asc()
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def claim_next_job(self, *, kinds: list[str]) -> BackgroundJob | None:
        now = _utc_now()
        expiry = now - timedelta(minutes=10)
        result = await self.session.execute(
            select(BackgroundJob)
            .where(
                BackgroundJob.kind.in_(kinds),
                BackgroundJob.status.in_(["queued", "retry"]),
                BackgroundJob.run_after <= now,
                or_(
                    BackgroundJob.locked_at.is_(None),
                    BackgroundJob.locked_at < expiry,
                ),
            )
            .order_by(BackgroundJob.created_at.asc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.locked_at = now
        job.attempt = job.attempt + 1
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def complete_job(
        self,
        *,
        job: BackgroundJob,
        result_payload: dict[str, object],
    ) -> None:
        job.status = "completed"
        job.result = result_payload
        job.error = None
        job.locked_at = None
        self.session.add(job)
        await self.session.commit()

    async def fail_job(self, *, job: BackgroundJob, error: str) -> None:
        now = _utc_now()
        should_retry = job.attempt < job.max_attempts
        job.status = "retry" if should_retry else "failed"
        job.error = error
        job.locked_at = None
        if should_retry:
            delay_seconds = min(300, 2**job.attempt)
            job.run_after = now + timedelta(seconds=delay_seconds)
        self.session.add(job)
        await self.session.commit()

    async def mark_stale_running_jobs(self) -> int:
        now = _utc_now()
        stale_before = now - timedelta(minutes=20)
        result = await self.session.execute(
            select(BackgroundJob).where(
                and_(
                    BackgroundJob.status == "running",
                    BackgroundJob.locked_at.is_not(None),
                    BackgroundJob.locked_at < stale_before,
                )
            )
        )
        jobs = list(result.scalars().all())
        for job in jobs:
            job.status = "retry" if job.attempt < job.max_attempts else "failed"
            job.locked_at = None
            if job.status == "retry":
                job.run_after = now
            self.session.add(job)
        if jobs:
            await self.session.commit()
        return len(jobs)
