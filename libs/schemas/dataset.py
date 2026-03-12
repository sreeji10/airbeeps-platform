from pydantic import BaseModel, Field

from libs.schemas.common import utc_now


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    file_id: str
    storage_bucket: str
    storage_path: str
    uploaded_at: str = Field(default_factory=lambda: utc_now().isoformat())


class DatasetRead(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    name: str
    status: str
    created_by: str
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
