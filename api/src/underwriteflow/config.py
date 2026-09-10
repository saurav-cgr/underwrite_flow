"""Runtime configuration for UnderwriteFlow."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated local runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://underwriteflow:synthetic-local-password@db:5432/"
        "underwriteflow"
    )
    generation_provider: Literal["fake", "gemini", "ollama"] = "gemini"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


# Reuse one validated settings instance per process.
@lru_cache
def get_settings() -> Settings:
    return Settings()
