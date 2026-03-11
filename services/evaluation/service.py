from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import (
    AgentConfig,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from libs.llm.base import LLMClient
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.evaluation import (
    EvaluationCaseCreateRequest,
    EvaluationDatasetCreateRequest,
    EvaluationRunCreateRequest,
)
from services.platform.service import PlatformService


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EvaluationService:
    session: AsyncSession
    llm: LLMClient | None

    async def create_dataset(
        self,
        *,
        request: EvaluationDatasetCreateRequest,
        user: AuthenticatedUser,
    ) -> EvaluationDataset:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        dataset = EvaluationDataset(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            name=request.name,
            description=request.description,
            created_by=user.user_id,
        )
        self.session.add(dataset)
        await self.session.commit()
        await self.session.refresh(dataset)
        return dataset

    async def add_case(
        self,
        *,
        request: EvaluationCaseCreateRequest,
        user: AuthenticatedUser,
    ) -> EvaluationCase:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        item = EvaluationCase(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            evaluation_dataset_id=request.evaluation_dataset_id,
            input_text=request.input_text,
            expected_text=request.expected_text,
            case_metadata=request.metadata,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def create_run(
        self,
        *,
        request: EvaluationRunCreateRequest,
        user: AuthenticatedUser,
    ) -> EvaluationRun:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        run = EvaluationRun(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            evaluation_dataset_id=request.evaluation_dataset_id,
            agent_id=request.agent_id,
            status="queued",
            summary={},
            created_by=user.user_id,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def execute_run(self, *, evaluation_run_id: str) -> dict[str, object]:
        run_result = await self.session.execute(
            select(EvaluationRun).where(EvaluationRun.id == evaluation_run_id)
        )
        run = run_result.scalar_one_or_none()
        if run is None:
            raise ValueError("Evaluation run not found")

        dataset_result = await self.session.execute(
            select(EvaluationDataset).where(
                EvaluationDataset.id == run.evaluation_dataset_id,
                EvaluationDataset.workspace_id == run.workspace_id,
            )
        )
        dataset = dataset_result.scalar_one_or_none()
        if dataset is None:
            raise ValueError("Evaluation dataset not found")

        agent_result = await self.session.execute(
            select(AgentConfig).where(
                AgentConfig.id == run.agent_id,
                AgentConfig.workspace_id == run.workspace_id,
            )
        )
        agent = agent_result.scalar_one_or_none()
        if agent is None:
            raise ValueError("Agent not found")

        run.status = "running"
        self.session.add(run)
        await self.session.commit()

        case_result = await self.session.execute(
            select(EvaluationCase).where(
                EvaluationCase.evaluation_dataset_id == dataset.id
            )
        )
        cases = list(case_result.scalars().all())
        if not cases:
            run.status = "completed"
            run.summary = {"case_count": 0, "average_score": 0.0}
            run.completed_at = _utc_now()
            self.session.add(run)
            await self.session.commit()
            return run.summary

        total_score = 0.0
        for case in cases:
            output = await self._execute_case(agent=agent, prompt=case.input_text)
            score, reasoning = self._score_output(
                output=output,
                expected=case.expected_text,
            )
            total_score += score
            item = EvaluationResult(
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                evaluation_run_id=run.id,
                evaluation_case_id=case.id,
                output_text=output,
                score=score,
                reasoning=reasoning,
                details={"agent_id": agent.id},
            )
            self.session.add(item)
            await self.session.commit()

        average_score = total_score / len(cases)
        run.status = "completed"
        run.summary = {
            "case_count": len(cases),
            "average_score": average_score,
            "dataset_id": dataset.id,
            "agent_id": agent.id,
        }
        run.completed_at = _utc_now()
        self.session.add(run)
        await self.session.commit()
        return run.summary

    async def list_run_results(
        self,
        *,
        evaluation_run_id: str,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> list[EvaluationResult]:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(EvaluationResult)
            .where(
                EvaluationResult.workspace_id == workspace_id,
                EvaluationResult.evaluation_run_id == evaluation_run_id,
            )
            .order_by(EvaluationResult.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_runs(
        self,
        *,
        workspace_id: str,
        project_id: str,
        user: AuthenticatedUser,
    ) -> list[EvaluationRun]:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(EvaluationRun)
            .where(
                EvaluationRun.workspace_id == workspace_id,
                EvaluationRun.project_id == project_id,
            )
            .order_by(EvaluationRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_run(
        self,
        *,
        run_id: str,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> EvaluationRun | None:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == run_id,
                EvaluationRun.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def _execute_case(self, *, agent: AgentConfig, prompt: str) -> str:
        if self.llm is None:
            raise RuntimeError("LLM client is required to execute evaluation cases")
        system_prompt = (
            f"You are evaluation agent '{agent.name}'. Provide concise responses."
        )
        return await self.llm.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        )

    def _score_output(
        self,
        *,
        output: str,
        expected: str | None,
    ) -> tuple[float, str]:
        if expected is None or not expected.strip():
            return 0.5, "No expected output provided; assigned neutral score."
        expected_clean = expected.strip().lower()
        output_clean = output.strip().lower()
        if expected_clean == output_clean:
            return 1.0, "Exact match."
        if expected_clean in output_clean:
            return 0.8, "Expected text appears in output."
        overlap = len(set(expected_clean.split()) & set(output_clean.split()))
        baseline = max(1, len(set(expected_clean.split())))
        return overlap / baseline, "Token overlap heuristic score."

    async def usage_snapshot(self, *, workspace_id: str) -> int:
        result = await self.session.execute(
            select(func.count(EvaluationRun.id)).where(
                EvaluationRun.workspace_id == workspace_id
            )
        )
        return int(result.scalar_one())
