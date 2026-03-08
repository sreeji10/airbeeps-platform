from pydantic import BaseModel, Field

from libs.schemas.common import utc_now
from libs.schemas.rag import RetrievedChunk


class ChatRunRequest(BaseModel):
    project_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
    dataset_ids: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)


class ChatRunResponse(BaseModel):
    run_id: str
    response: str
    steps: list[str]
    retrieval: list[RetrievedChunk]
    used_tools: list[str]
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
