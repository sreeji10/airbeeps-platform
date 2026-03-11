from __future__ import annotations

import asyncio

from services.evaluation.service import EvaluationService
from services.jobs.service import JobService
from services.jobs.worker import JobWorker

from airbeeps_api.db.session import SessionLocal
from airbeeps_api.dependencies import get_container


async def run_worker_loop(*, interval_seconds: float = 2.0) -> None:
    container = get_container()
    while True:
        processed = False
        async with SessionLocal() as session:
            jobs = JobService(session)
            await jobs.mark_stale_running_jobs()
            worker = JobWorker(
                session=session,
                jobs=jobs,
                ingestion=container.ingestion,
                evaluation=EvaluationService(session=session, llm=container.llm),
            )
            processed = await worker.run_once()
        if not processed:
            await asyncio.sleep(interval_seconds)


def main() -> None:
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
