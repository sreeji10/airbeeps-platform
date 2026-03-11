from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    workspace_id: str
    project_id: str | None = None
    kind: str = Field(min_length=1, max_length=64)
    payload: dict[str, object] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)


class JobRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str | None
    kind: str
    status: str
    payload: dict[str, object]
    result: dict[str, object]
    error: str | None
    attempt: int
    max_attempts: int
    run_after: str
    created_by: str
    created_at: str
    updated_at: str
