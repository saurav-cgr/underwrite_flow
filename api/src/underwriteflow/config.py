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
    jwt_issuer: str = "underwriteflow"
    jwt_audience: str = "underwriteflow-web"
    access_token_ttl_seconds: int = Field(default=900, gt=0, le=86_400)
    refresh_token_ttl_seconds: int = Field(
        default=28_800, gt=0, le=2_592_000
    )
    refresh_token_pepper: str = "synthetic-local-refresh-pepper"
    upload_root: str = "/data/uploads"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


# Reuse one validated settings instance per process.
@lru_cache
def get_settings() -> Settings:
    return Settings()
