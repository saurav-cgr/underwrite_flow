"""Unit coverage for provider builders using common model settings."""

import pytest

from underwriteflow.config import Settings
from underwriteflow.providers.factory import build_provider
from underwriteflow.providers.gemini import GeminiProvider
from underwriteflow.providers.guidance import (
    GeminiGuidanceProvider,
    build_guidance_provider,
)
from underwriteflow.providers.ollama import OllamaProvider
from underwriteflow.providers.service import ProviderError


# Verify provider defaults reach extraction adapters without requests.
@pytest.mark.parametrize(
    ("provider", "expected", "provider_type"),
    (
        ("gemini", "gemini-3.1-flash-lite", GeminiProvider),
        ("ollama", "llama3.2", OllamaProvider),
    ),
)
def test_extraction_builder_uses_resolved_generation_default(
    provider: str,
    expected: str,
    provider_type: type[GeminiProvider] | type[OllamaProvider],
) -> None:
    settings = Settings(
        _env_file=None,
        generation_provider=provider,
        generation_model=None,
        gemini_api_key="synthetic-key",
        gemini_no_training_acknowledged=True,
    )

    result = build_provider(settings)

    assert isinstance(result, provider_type)
    assert result.model == expected


# Verify one generation override reaches Gemini extraction and guidance.
def test_gemini_builders_share_common_generation_override() -> None:
    settings = Settings(
        _env_file=None,
        generation_provider="gemini",
        generation_model=" shared-model ",
        gemini_api_key="synthetic-key",
        gemini_no_training_acknowledged=True,
    )

    extraction = build_provider(settings)
    guidance = build_guidance_provider(settings)

    assert isinstance(extraction, GeminiProvider)
    assert isinstance(guidance, GeminiGuidanceProvider)
    assert extraction.model == "shared-model"
    assert guidance.model == "shared-model"


# Verify fake providers ignore common generation model overrides.
def test_fake_builders_ignore_common_generation_override() -> None:
    settings = Settings(
        _env_file=None,
        generation_provider="fake",
        generation_model="unused-model",
    )

    extraction = build_provider(settings)
    guidance = build_guidance_provider(settings)

    assert extraction.name == "fake"
    assert guidance is not None
    assert guidance.name == "fake"


# Verify local Ollama keeps unavailable guidance despite a common override.
def test_ollama_guidance_remains_unavailable() -> None:
    settings = Settings(
        _env_file=None,
        generation_provider="ollama",
        generation_model="local-model",
    )

    assert build_guidance_provider(settings) is None


# Verify Gemini safeguards remain before adapter construction.
def test_gemini_builder_keeps_training_and_host_guards() -> None:
    with pytest.raises(ProviderError, match="no-training"):
        build_provider(
            Settings(
                _env_file=None,
                generation_provider="gemini",
                generation_model="shared-model",
                gemini_no_training_acknowledged=False,
            )
        )

    with pytest.raises(ProviderError, match="host"):
        build_guidance_provider(
            Settings(
                _env_file=None,
                generation_provider="gemini",
                generation_model="shared-model",
                gemini_no_training_acknowledged=True,
                provider_allowed_hosts=("ollama",),
            )
        )
