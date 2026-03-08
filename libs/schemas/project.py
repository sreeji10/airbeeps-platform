from pydantic import BaseModel, Field

from libs.schemas.common import utc_now


class ProjectCreateRequest(BaseModel):
    workspace_id: str
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    created_by: str
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
