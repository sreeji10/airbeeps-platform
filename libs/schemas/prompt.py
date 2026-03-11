from pydantic import BaseModel, Field


class PromptTemplateCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    name: str = Field(min_length=1, max_length=128)
    version: int = Field(default=1, ge=1, le=1000)
    template: str = Field(min_length=1, max_length=20000)
    variables: list[str] = Field(default_factory=list, max_length=100)


class PromptTemplateRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    name: str
    version: int
    template: str
    variables: list[str]
    created_by: str
    created_at: str
