from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import BackgroundJob
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.ingestion import IngestDatasetRequest
from services.evaluation.service import EvaluationService
from services.ingestion.service import IngestionService
from services.jobs.service import JobService


@dataclass
class JobWorker:
    session: AsyncSession
    jobs: JobService
    ingestion: IngestionService
    evaluation: EvaluationService

    async def run_once(self) -> bool:
        job = await self.jobs.claim_next_job(
            kinds=["dataset_ingestion", "evaluation_run"]
        )
        if job is None:
            return False
        try:
            result = await self._execute(job)
            await self.jobs.complete_job(job=job, result_payload=result)
        except Exception as exc:
            await self.jobs.fail_job(job=job, error=str(exc))
        return True

    async def _execute(self, job: BackgroundJob) -> dict[str, object]:
        if job.kind == "dataset_ingestion":
            request = IngestDatasetRequest.model_validate(job.payload)
            user = AuthenticatedUser(user_id=job.created_by)
            response = await self.ingestion.ingest(
                session=self.session,
                request=request,
                user=user,
            )
            return {
                "dataset_id": response.dataset_id,
                "status": response.status,
                "chunk_count": response.chunk_count,
            }
        if job.kind == "evaluation_run":
            run_id = str(job.payload.get("evaluation_run_id", ""))
            summary = await self.evaluation.execute_run(evaluation_run_id=run_id)
            return {"evaluation_run_id": run_id, "summary": summary}
        raise ValueError(f"Unsupported job kind '{job.kind}'")
