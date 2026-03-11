from dataclasses import dataclass
from functools import lru_cache

from libs.llm.base import LLMClient
from libs.tools.registry import ToolRegistry, build_default_tool_registry
from services.auth.supabase_jwt import SupabaseJwtVerifier
from services.ingestion.service import IngestionService, SupabaseIngestionService
from services.llm.litellm_client import LiteLLMClient
from services.llm.litellm_embedding import LiteLLMEmbeddingClient
from services.rag.service import PostgresRagService, RagService
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
    jwt_verifier = SupabaseJwtVerifier(settings=settings)
    storage_service = SupabaseStorageService(settings=settings)
    llm_client = LiteLLMClient(
        model=settings.llm_model,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
    )
    embedding_client = LiteLLMEmbeddingClient(
        model=settings.embedding_model,
        provider=settings.embedding_provider,
        api_key=settings.embedding_api_key or settings.llm_api_key,
        base_url=settings.embedding_base_url or settings.llm_base_url,
    )
    rag_service = PostgresRagService(
        embeddings=embedding_client,
        storage=storage_service,
        default_top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    ingestion_service = SupabaseIngestionService(rag=rag_service)

    return ServiceContainer(
        settings=settings,
        rag=rag_service,
        ingestion=ingestion_service,
        tools=tools,
        jwt_verifier=jwt_verifier,
        storage=storage_service,
        llm=llm_client,
    )
