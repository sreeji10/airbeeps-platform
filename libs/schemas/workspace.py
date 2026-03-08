from pydantic import BaseModel, Field

from libs.schemas.common import utc_now


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
