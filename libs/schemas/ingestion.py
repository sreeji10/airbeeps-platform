from pydantic import BaseModel, Field

from libs.schemas.common import utc_now


class IngestDatasetRequest(BaseModel):
    project_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    files: list[str] = Field(default_factory=list, min_length=1)


class IngestDatasetResponse(BaseModel):
    job_id: str
    project_id: str
    dataset_id: str
    status: str
    accepted_files: int
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
