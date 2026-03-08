from pydantic import BaseModel, Field

from libs.schemas.common import utc_now


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    file_id: str
    storage_bucket: str
    storage_path: str
    uploaded_at: str = Field(default_factory=lambda: utc_now().isoformat())
