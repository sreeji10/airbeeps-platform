from fastapi import APIRouter, Depends
from libs.schemas.ingestion import IngestDatasetRequest, IngestDatasetResponse

from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/ingest", response_model=IngestDatasetResponse)
def ingest_dataset(
    request: IngestDatasetRequest,
    container: ServiceContainer = Depends(get_container),
) -> IngestDatasetResponse:
    return container.ingestion.ingest(request=request)
