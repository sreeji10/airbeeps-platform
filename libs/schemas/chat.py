from typing import Literal

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


class ChatCreateRequest(BaseModel):
    workspace_id: str
    project_id: str
    title: str | None = Field(default=None, max_length=255)


class ChatCreateResponse(BaseModel):
    chat_id: str
    workspace_id: str
    project_id: str
    title: str | None = None
    created_at: str


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageRead(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_by: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: list[ChatMessageRead]


class ChatTurnResponse(BaseModel):
    chat_id: str
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    plan_id: str
    run_id: str
    run_status: str
