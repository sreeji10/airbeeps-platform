from fastapi import APIRouter, Depends, HTTPException
from libs.db.models import (
    BackgroundJob,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.evaluation import (
    EvaluationCaseCreateRequest,
    EvaluationCaseRead,
    EvaluationDatasetCreateRequest,
    EvaluationDatasetRead,
    EvaluationResultRead,
    EvaluationRunCreateRequest,
    EvaluationRunRead,
)
from libs.schemas.job import JobCreateRequest, JobRead
from services.evaluation.service import EvaluationService
from services.jobs.service import JobService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _dataset_read(row: EvaluationDataset) -> EvaluationDatasetRead:
    return EvaluationDatasetRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        name=row.name,
        description=row.description,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )


def _case_read(row: EvaluationCase) -> EvaluationCaseRead:
    return EvaluationCaseRead(
        id=row.id,
        evaluation_dataset_id=row.evaluation_dataset_id,
        input_text=row.input_text,
        expected_text=row.expected_text,
        metadata=dict(row.case_metadata),
        created_at=row.created_at.isoformat(),
    )


def _run_read(row: EvaluationRun) -> EvaluationRunRead:
    return EvaluationRunRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        evaluation_dataset_id=row.evaluation_dataset_id,
        agent_id=row.agent_id,
        status=row.status,
        summary=dict(row.summary),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at is not None else None,
    )


def _result_read(row: EvaluationResult) -> EvaluationResultRead:
    return EvaluationResultRead(
        id=row.id,
        evaluation_run_id=row.evaluation_run_id,
        evaluation_case_id=row.evaluation_case_id,
        output_text=row.output_text,
        score=row.score,
        reasoning=row.reasoning,
        details=dict(row.details),
        created_at=row.created_at.isoformat(),
    )


def _job_read(row: BackgroundJob) -> JobRead:
    return JobRead(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        kind=row.kind,
        status=row.status,
        payload=dict(row.payload),
        result=dict(row.result),
        error=row.error,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        run_after=row.run_after.isoformat(),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


@router.post("/datasets", response_model=EvaluationDatasetRead)
async def create_evaluation_dataset(
    request: EvaluationDatasetCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationDatasetRead:
    service = EvaluationService(session=session, llm=None)
    try:
        row = await service.create_dataset(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _dataset_read(row)


@router.post("/cases", response_model=EvaluationCaseRead)
async def create_evaluation_case(
    request: EvaluationCaseCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationCaseRead:
    service = EvaluationService(session=session, llm=None)
    try:
        row = await service.add_case(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _case_read(row)


@router.post("/runs", response_model=JobRead)
async def enqueue_evaluation_run(
    request: EvaluationRunCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    eval_service = EvaluationService(session=session, llm=None)
    try:
        run = await eval_service.create_run(request=request, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    jobs = JobService(session=session)
    job = await jobs.enqueue(
        request=JobCreateRequest(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            kind="evaluation_run",
            payload={"evaluation_run_id": run.id},
        ),
        user=user,
    )
    return _job_read(job)


@router.get("/runs", response_model=list[EvaluationRunRead])
async def list_evaluation_runs(
    workspace_id: str,
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[EvaluationRunRead]:
    service = EvaluationService(session=session, llm=None)
    rows = await service.list_runs(
        workspace_id=workspace_id,
        project_id=project_id,
        user=user,
    )
    return [_run_read(row) for row in rows]


@router.get("/runs/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation_run(
    run_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationRunRead:
    service = EvaluationService(session=session, llm=None)
    row = await service.get_run(run_id=run_id, workspace_id=workspace_id, user=user)
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return _run_read(row)


@router.get("/runs/{run_id}/results", response_model=list[EvaluationResultRead])
async def list_evaluation_results(
    run_id: str,
    workspace_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[EvaluationResultRead]:
    service = EvaluationService(session=session, llm=None)
    rows = await service.list_run_results(
        evaluation_run_id=run_id,
        workspace_id=workspace_id,
        user=user,
    )
    return [_result_read(row) for row in rows]
