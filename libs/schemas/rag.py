from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    dataset_id: str
    chunk_id: str
    score: float = Field(ge=0.0, le=1.0)
    content: str
    citation: str
