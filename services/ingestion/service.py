from libs.schemas.ingestion import IngestDatasetRequest, IngestDatasetResponse
from libs.utils.ids import make_id


class IngestionService:
    def ingest(self, request: IngestDatasetRequest) -> IngestDatasetResponse:
        raise NotImplementedError


class InMemoryIngestionService(IngestionService):
    def ingest(self, request: IngestDatasetRequest) -> IngestDatasetResponse:
        return IngestDatasetResponse(
            job_id=make_id("ingest"),
            project_id=request.project_id,
            dataset_id=request.dataset_id,
            status="accepted",
            accepted_files=len(request.files),
        )
