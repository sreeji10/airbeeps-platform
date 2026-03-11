from dataclasses import dataclass
from functools import lru_cache

from libs.embeddings.base import EmbeddingClient
from libs.llm.base import LLMClient
from libs.tools.registry import ToolRegistry
from services.auth.supabase_jwt import SupabaseJwtVerifier
from services.ingestion.service import IngestionService, SupabaseIngestionService
from services.llm.litellm_client import LiteLLMClient
from services.llm.litellm_embedding import LiteLLMEmbeddingClient
from services.llm.routing import ModelRouter
from services.memory.service import MemoryService
from services.rag.service import PostgresRagService, RagService
from services.runtime.tools import RuntimeToolsFactory
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
    embeddings: EmbeddingClient
    model_router: ModelRouter
    memory: MemoryService


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    settings = get_settings()
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
    model_router = ModelRouter(
        default_model=settings.llm_model,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
    )
    rag_service = PostgresRagService(
        embeddings=embedding_client,
        storage=storage_service,
        default_top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    memory_service = MemoryService(embeddings=embedding_client)
    tools = RuntimeToolsFactory(
        rag=rag_service,
        default_retrieval_top_k=settings.rag_top_k,
        memory=memory_service,
        default_memory_top_k=settings.memory_top_k,
        http_timeout_seconds=settings.runtime_http_timeout_seconds,
    ).build_registry()
    ingestion_service = SupabaseIngestionService(rag=rag_service)

    return ServiceContainer(
        settings=settings,
        rag=rag_service,
        ingestion=ingestion_service,
        tools=tools,
        jwt_verifier=jwt_verifier,
        storage=storage_service,
        llm=llm_client,
        embeddings=embedding_client,
        model_router=model_router,
        memory=memory_service,
    )
