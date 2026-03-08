from dataclasses import dataclass

from libs.schemas.rag import RetrievedChunk


class RagService:
    def retrieve(
        self, query: str, dataset_ids: list[str], top_k: int
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


@dataclass
class InMemoryRagService(RagService):
    default_top_k: int = 5

    def retrieve(
        self, query: str, dataset_ids: list[str], top_k: int
    ) -> list[RetrievedChunk]:
        limit = max(1, min(top_k, self.default_top_k))
        resolved_datasets = dataset_ids or ["default-dataset"]
        results: list[RetrievedChunk] = []

        for index in range(limit):
            dataset_id = resolved_datasets[index % len(resolved_datasets)]
            results.append(
                RetrievedChunk(
                    dataset_id=dataset_id,
                    chunk_id=f"chunk-{index + 1}",
                    score=round(1.0 - (index * 0.1), 2),
                    content=f"Placeholder retrieval result for query '{query}'.",
                    citation=f"{dataset_id}:chunk-{index + 1}",
                )
            )
        return results
