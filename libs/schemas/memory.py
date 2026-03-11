from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    agent_id: str | None = None
    source_chat_id: str | None = None
    content: str = Field(min_length=1, max_length=12000)
    metadata: dict[str, object] = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    workspace_id: str
    project_id: str
    query: str = Field(min_length=1, max_length=4000)
    agent_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class MemoryRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    agent_id: str | None
    source_chat_id: str | None
    content: str
    score: float | None = None
    metadata: dict[str, object]
    created_by: str
    created_at: str
