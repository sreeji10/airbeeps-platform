from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    planner_model: str | None = Field(default=None, max_length=255)
    generation_model: str | None = Field(default=None, max_length=255)
    fallback_model: str | None = Field(default=None, max_length=255)
    prompt_template_id: str | None = None
    enabled_tools: list[str] = Field(default_factory=list, max_length=100)
    dataset_ids: list[str] = Field(default_factory=list, max_length=100)
    execution_limits: dict[str, object] = Field(default_factory=dict)


class AgentRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    name: str
    description: str | None
    planner_model: str | None
    generation_model: str | None
    fallback_model: str | None
    prompt_template_id: str | None
    enabled_tools: list[str]
    dataset_ids: list[str]
    execution_limits: dict[str, object]
    status: str
    created_by: str
    created_at: str
