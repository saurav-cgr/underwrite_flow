"""Unit coverage for common provider model configuration."""

import pytest

from underwriteflow.config import Settings


MODEL_ENVIRONMENT = (
    "GENERATION_PROVIDER",
    "EMBEDDING_PROVIDER",
    "GENERATION_MODEL",
    "EMBEDDING_MODEL",
    "GEMINI_MODEL",
    "OLLAMA_MODEL",
    "GEMINI_EMBEDDING_MODEL",
    "OLLAMA_EMBEDDING_MODEL",
)


# Clear model settings so tests do not read Docker or dotenv configuration.
@pytest.fixture
def clean_model_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in MODEL_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


# Verify selected generation providers resolve their contract defaults.
@pytest.mark.parametrize(
    ("provider", "expected"),
    (
        ("gemini", "gemini-3.1-flash-lite"),
        ("ollama", "llama3.2"),
        ("fake", None),
    ),
)
def test_generation_model_defaults_follow_provider(
    clean_model_environment: None,
    provider: str,
    expected: str | None,
) -> None:
    settings = Settings(_env_file=None, generation_provider=provider)

    assert settings.resolved_generation_model == expected


# Verify embedding selection falls back to selected generation provider.
@pytest.mark.parametrize(
    ("provider", "expected"),
    (
        ("gemini", "gemini-embedding-001"),
        ("ollama", "embeddinggemma"),
        ("fake", None),
    ),
)
def test_embedding_model_defaults_follow_effective_provider(
    clean_model_environment: None,
    provider: str,
    expected: str | None,
) -> None:
    settings = Settings(
        _env_file=None,
        generation_provider=provider,
        embedding_provider=None,
    )

    assert settings.resolved_embedding_model == expected


# Verify common overrides apply independently to selected capabilities.
def test_common_model_overrides_support_mixed_providers(
    clean_model_environment: None,
) -> None:
    settings = Settings(
        _env_file=None,
        generation_provider="ollama",
        embedding_provider="gemini",
        generation_model=" local-generation ",
        embedding_model=" remote-embedding ",
    )

    assert settings.generation_model == "local-generation"
    assert settings.embedding_model == "remote-embedding"
    assert settings.resolved_generation_model == "local-generation"
    assert settings.resolved_embedding_model == "remote-embedding"


# Verify blank overrides use defaults after surrounding whitespace is removed.
@pytest.mark.parametrize("value", ("", "   ", "\t"))
def test_blank_model_overrides_resolve_to_none(
    clean_model_environment: None,
    value: str,
) -> None:
    settings = Settings(
        _env_file=None,
        generation_provider="gemini",
        embedding_provider="ollama",
        generation_model=value,
        embedding_model=value,
    )

    assert settings.generation_model is None
    assert settings.embedding_model is None
    assert settings.resolved_generation_model == "gemini-3.1-flash-lite"
    assert settings.resolved_embedding_model == "embeddinggemma"


# Verify environment overrides trim values and ignore former model names.
def test_environment_models_override_without_legacy_selection(
    clean_model_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENERATION_MODEL", " model-from-environment ")
    monkeypatch.setenv("EMBEDDING_MODEL", " embedding-from-environment ")
    monkeypatch.setenv("GEMINI_MODEL", "legacy-generation")
    monkeypatch.setenv("GEMINI_EMBEDDING_MODEL", "legacy-embedding")
    settings = Settings(
        _env_file=None,
        generation_provider="gemini",
        embedding_provider="gemini",
    )

    assert settings.generation_model == "model-from-environment"
    assert settings.embedding_model == "embedding-from-environment"
    assert settings.resolved_generation_model == "model-from-environment"
    assert settings.resolved_embedding_model == "embedding-from-environment"


# Verify removed provider-specific settings cannot affect model selection.
def test_legacy_model_fields_are_removed(
    clean_model_environment: None,
) -> None:
    settings = Settings(_env_file=None)

    for field in (
        "gemini_model",
        "ollama_model",
        "gemini_embedding_model",
        "ollama_embedding_model",
    ):
        assert field not in Settings.model_fields
        assert not hasattr(settings, field)
