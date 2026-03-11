from pydantic import BaseModel, Field


class EvaluationDatasetCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class EvaluationDatasetRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    name: str
    description: str | None
    created_by: str
    created_at: str


class EvaluationCaseCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    evaluation_dataset_id: str
    input_text: str = Field(min_length=1, max_length=12000)
    expected_text: str | None = Field(default=None, max_length=12000)
    metadata: dict[str, object] = Field(default_factory=dict)


class EvaluationCaseRead(BaseModel):
    id: str
    evaluation_dataset_id: str
    input_text: str
    expected_text: str | None
    metadata: dict[str, object]
    created_at: str


class EvaluationRunCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    evaluation_dataset_id: str
    agent_id: str


class EvaluationRunRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    evaluation_dataset_id: str
    agent_id: str
    status: str
    summary: dict[str, object]
    created_by: str
    created_at: str
    completed_at: str | None


class EvaluationResultRead(BaseModel):
    id: str
    evaluation_run_id: str
    evaluation_case_id: str
    output_text: str
    score: float
    reasoning: str | None
    details: dict[str, object]
    created_at: str
