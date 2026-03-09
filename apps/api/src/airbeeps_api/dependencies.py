from dataclasses import dataclass
from functools import lru_cache

from libs.llm.base import LLMClient
from libs.tools.registry import ToolRegistry, build_default_tool_registry
from services.auth.supabase_jwt import SupabaseJwtVerifier
from services.ingestion.service import IngestionService, InMemoryIngestionService
from services.llm.litellm_client import LiteLLMClient
from services.rag.service import InMemoryRagService, RagService
from services.storage.supabase_storage import SupabaseStorageService

from airbeeps_api.core.config import Settings, get_settings


@dataclass(frozen=True)
class ServiceContainer:
    settings: Settings
    rag: RagService
    ingestion: IngestionService
    tools: ToolRegistry
    jwt_verifier: SupabaseJwtVerifier
    storage: SupabaseStorageService
    llm: LLMClient


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    settings = get_settings()
    tools = build_default_tool_registry()
    rag_service = InMemoryRagService(default_top_k=settings.rag_top_k)
    ingestion_service = InMemoryIngestionService()
    jwt_verifier = SupabaseJwtVerifier(settings=settings)
    storage_service = SupabaseStorageService(settings=settings)
    llm_client = LiteLLMClient(
        model=settings.llm_model,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
    )
    return ServiceContainer(
        settings=settings,
        rag=rag_service,
        ingestion=ingestion_service,
        tools=tools,
        jwt_verifier=jwt_verifier,
        storage=storage_service,
        llm=llm_client,
    )
