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
    rag_top_k: int = Field(default=5, ge=1, le=20)
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
