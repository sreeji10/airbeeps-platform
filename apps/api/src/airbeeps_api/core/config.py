from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Airbeeps API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    api_prefix: str = "/v1"
    log_level: str = "INFO"
    log_json: bool = False
    docs_enabled: bool = True
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    rag_top_k: int = Field(default=5, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AIRBEEPS_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
