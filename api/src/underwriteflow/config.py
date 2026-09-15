"""Runtime configuration for UnderwriteFlow."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated local runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://underwriteflow:synthetic-local-password@db:5433/"
        "underwriteflow"
    )
    generation_provider: Literal["fake", "gemini", "ollama"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"
    provider_timeout_seconds: float = Field(default=30, gt=0)
    provider_retry_count: int = Field(default=2, ge=0, le=5)
    session_secret: str = "synthetic-local-session-secret"
    session_ttl_seconds: int = Field(default=900, gt=0, le=86_400)
    upload_root: str = "/data/uploads"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


# Reuse one validated settings instance per process.
@lru_cache
def get_settings() -> Settings:
    return Settings()
