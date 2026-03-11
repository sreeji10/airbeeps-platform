from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    app_name: str = Field(
        default="Airbeeps API", validation_alias=AliasChoices("APP_NAME", "AIRBEEPS_APP_NAME")
    )
    app_env: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "AIRBEEPS_APP_ENV"),
    )
    app_version: str = Field(
        default="0.1.0", validation_alias=AliasChoices("APP_VERSION", "AIRBEEPS_APP_VERSION")
    )
    api_prefix: str = Field(
        default="/v1", validation_alias=AliasChoices("API_PREFIX", "AIRBEEPS_API_PREFIX")
    )
    log_level: str = Field(
        default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "AIRBEEPS_LOG_LEVEL")
    )
    log_json: bool = Field(
        default=False, validation_alias=AliasChoices("LOG_JSON", "AIRBEEPS_LOG_JSON")
    )
    docs_enabled: bool = Field(
        default=True, validation_alias=AliasChoices("DOCS_ENABLED", "AIRBEEPS_DOCS_ENABLED")
    )
    request_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        validation_alias=AliasChoices(
            "REQUEST_TIMEOUT_SECONDS", "AIRBEEPS_REQUEST_TIMEOUT_SECONDS"
        ),
    )
    rag_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias=AliasChoices("RAG_TOP_K", "AIRBEEPS_RAG_TOP_K"),
    )
    rag_chunk_size: int = Field(
        default=1200,
        ge=200,
        le=4000,
        validation_alias=AliasChoices("RAG_CHUNK_SIZE", "AIRBEEPS_RAG_CHUNK_SIZE"),
    )
    rag_chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        validation_alias=AliasChoices("RAG_CHUNK_OVERLAP", "AIRBEEPS_RAG_CHUNK_OVERLAP"),
    )
    runtime_tool_max_iterations: int = Field(
        default=4,
        ge=1,
        le=12,
        validation_alias=AliasChoices(
            "RUNTIME_TOOL_MAX_ITERATIONS", "AIRBEEPS_RUNTIME_TOOL_MAX_ITERATIONS"
        ),
    )
    runtime_http_timeout_seconds: float = Field(
        default=8.0,
        ge=0.5,
        le=30.0,
        validation_alias=AliasChoices(
            "RUNTIME_HTTP_TIMEOUT_SECONDS", "AIRBEEPS_RUNTIME_HTTP_TIMEOUT_SECONDS"
        ),
    )
    workspace_requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=5000,
        validation_alias=AliasChoices(
            "WORKSPACE_REQUESTS_PER_MINUTE",
            "AIRBEEPS_WORKSPACE_REQUESTS_PER_MINUTE",
        ),
    )
    llm_estimated_cost_per_1k_tokens: float = Field(
        default=0.001,
        ge=0.0,
        le=10.0,
        validation_alias=AliasChoices(
            "LLM_ESTIMATED_COST_PER_1K_TOKENS",
            "AIRBEEPS_LLM_ESTIMATED_COST_PER_1K_TOKENS",
        ),
    )
    memory_top_k: int = Field(
        default=4,
        ge=1,
        le=20,
        validation_alias=AliasChoices("MEMORY_TOP_K", "AIRBEEPS_MEMORY_TOP_K"),
    )
    db_echo: bool = Field(
        default=False, validation_alias=AliasChoices("DB_ECHO", "AIRBEEPS_DB_ECHO")
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
        validation_alias="DATABASE_URL",
    )
    supabase_url: str = Field(default="http://127.0.0.1:54321", validation_alias="SUPABASE_URL")
    supabase_publishable_key: str = Field(
        default="replace-me",
        validation_alias="SUPABASE_PUBLISHABLE_KEY",
    )
    supabase_secret_key: str = Field(
        default="replace-me",
        validation_alias="SUPABASE_SECRET_KEY",
    )
    supabase_jwt_audience: str = Field(
        default="authenticated", validation_alias="SUPABASE_JWT_AUDIENCE"
    )
    supabase_storage_bucket: str = Field(
        default="datasets", validation_alias="SUPABASE_STORAGE_BUCKET"
    )
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    llm_provider: str | None = Field(default=None, validation_alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0, validation_alias="LLM_TEMPERATURE")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_provider: str | None = Field(default=None, validation_alias="EMBEDDING_PROVIDER")
    embedding_api_key: str | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, validation_alias="EMBEDDING_BASE_URL")
    chat_system_prompt: str = Field(
        default="You are Airbeeps, an AI assistant helping users inside their workspace.",
        validation_alias="CHAT_SYSTEM_PROMPT",
    )
    chat_context_window_messages: int = Field(
        default=20, ge=1, le=200, validation_alias="CHAT_CONTEXT_WINDOW_MESSAGES"
    )

    model_config = SettingsConfigDict(
        env_file=("apps/api/.env", ".env"),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url_async(self) -> str:
        url = make_url(self.database_url)
        if not url.drivername.startswith("postgresql"):
            return self.database_url
        if url.drivername == "postgresql+asyncpg":
            return self.database_url
        return str(url.set(drivername="postgresql+asyncpg"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
