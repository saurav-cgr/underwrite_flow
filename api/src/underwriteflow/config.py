"""Runtime configuration for UnderwriteFlow."""

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

PiiRedactionTerm = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ProviderHost = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=253),
]
GEMINI_GENERATION_MODEL = "gemini-3.1-flash-lite"
GEMINI_EMBEDDING_DEFAULT = "gemini-embedding-001"
OLLAMA_GENERATION_MODEL = "llama3.2"
OLLAMA_EMBEDDING_DEFAULT = "embeddinggemma"


# Convert blank model overrides into automatic provider selection.
def normalize_model_override(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip() or None
    return value


ModelOverride = Annotated[
    str | None, BeforeValidator(normalize_model_override)
]


class Settings(BaseSettings):
    """Validated local runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", frozen=True
    )

    environment_mode: Literal[
        "development", "evaluation", "production"
    ] = "development"
    database_url: str = (
        "postgresql+asyncpg://underwriteflow:synthetic-local-password@db:5433/"
        "underwriteflow"
    )
    generation_provider: Literal["fake", "gemini", "ollama"] = "gemini"
    embedding_provider: Literal["fake", "gemini", "ollama"] | None = None
    generation_model: ModelOverride = None
    embedding_model: ModelOverride = None
    gemini_api_key: str = ""
    gemini_no_training_acknowledged: bool = False
    provider_allowed_hosts: tuple[ProviderHost, ...] = Field(
        default=("generativelanguage.googleapis.com", "ollama"),
        min_length=1,
        max_length=10,
    )
    pii_redaction_terms: tuple[PiiRedactionTerm, ...] = Field(
        default=(), max_length=50
    )
    ollama_base_url: str = "http://ollama:11434"
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
    regulatory_root: str = "/app/data/regulatory"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    # Resolve the selected generation model without changing fake identity.
    @property
    def resolved_generation_model(self) -> str | None:
        if self.generation_provider == "fake":
            return None
        if self.generation_model:
            return self.generation_model
        if self.generation_provider == "gemini":
            return GEMINI_GENERATION_MODEL
        return OLLAMA_GENERATION_MODEL

    # Resolve embeddings against their selected or fallback provider.
    @property
    def resolved_embedding_model(self) -> str | None:
        provider = self.embedding_provider or self.generation_provider
        if provider == "fake":
            return None
        if self.embedding_model:
            return self.embedding_model
        if provider == "gemini":
            return GEMINI_EMBEDDING_DEFAULT
        return OLLAMA_EMBEDDING_DEFAULT

    # Report whether this process may load the evaluation corpus.
    @property
    def evaluation_loading_allowed(self) -> bool:
        return self.environment_mode != "production"


# Reuse one validated settings instance per process.
@lru_cache
def get_settings() -> Settings:
    return Settings()
