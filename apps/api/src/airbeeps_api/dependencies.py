from dataclasses import dataclass
from functools import lru_cache

from libs.tools.registry import ToolRegistry, build_default_tool_registry
from services.ingestion.service import IngestionService, InMemoryIngestionService
from services.rag.service import InMemoryRagService, RagService
from services.runtime.service import RuntimeService, RuntimeServiceImpl

from airbeeps_api.core.config import get_settings


@dataclass(frozen=True)
class ServiceContainer:
    runtime: RuntimeService
    rag: RagService
    ingestion: IngestionService
    tools: ToolRegistry


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    settings = get_settings()
    tools = build_default_tool_registry()
    rag_service = InMemoryRagService(default_top_k=settings.rag_top_k)
    ingestion_service = InMemoryIngestionService()
    runtime_service = RuntimeServiceImpl(rag=rag_service, tools=tools)
    return ServiceContainer(
        runtime=runtime_service,
        rag=rag_service,
        ingestion=ingestion_service,
        tools=tools,
    )
