import json
import math

import httpx
import pytest

from underwriteflow.config import Settings
from underwriteflow.providers.embedding import (
    FakeEmbeddingProvider,
    GeminiEmbeddingProvider,
    build_embedding_provider,
)
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
)


# Measure cosine similarity for deterministic fake embedding assertions.
def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


# Verify fake embeddings are deterministic, normalized, and semantic enough.
@pytest.mark.asyncio
async def test_fake_embeddings_are_deterministic_and_unit_length() -> None:
    provider = FakeEmbeddingProvider()
    first = await provider.embed(["high cover review"])
    second = await provider.embed(["high cover review"])
    related = await provider.embed(["high cover specialist review"])
    unrelated = await provider.embed(["identity evidence"])

    assert first == second
    assert len(first[0]) == 768
    assert math.isclose(math.sqrt(cosine(first[0], first[0])), 1.0)
    assert cosine(first[0], related[0]) > cosine(first[0], unrelated[0])


# Verify Gemini sends redacted batched content to the approved endpoint.
@pytest.mark.asyncio
async def test_gemini_embedding_request_is_redacted() -> None:
    requests: list[httpx.Request] = []

    # Capture provider requests without making a network call.
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"embeddings": [{"values": [0.0] * 768}]},
        )

    provider = GeminiEmbeddingProvider(
        api_key="synthetic-secret",
        model="gemini-embedding-001",
        pii_redaction_terms=("Synthetic Person",),
        transport=httpx.MockTransport(handler),
    )
    result = await provider.embed(
        ["Synthetic Person email@example.test 9876543210"]
    )

    assert len(result) == 1
    assert requests[0].url.host == "generativelanguage.googleapis.com"
    assert requests[0].url.path.endswith(":batchEmbedContents")
    assert "synthetic-secret" not in str(requests[0].url)
    assert requests[0].headers["x-goog-api-key"] == "synthetic-secret"
    payload = json.loads(requests[0].content)
    assert payload["requests"][0]["outputDimensionality"] == 768
    assert "Synthetic Person" not in requests[0].content.decode()
    assert "email@example.test" not in requests[0].content.decode()
    assert "9876543210" not in requests[0].content.decode()
    assert "synthetic-secret" not in str(result)


# Verify transient Gemini statuses are safe to retry without leaking secrets.
@pytest.mark.asyncio
@pytest.mark.parametrize("status", [408, 429, 500, 503])
async def test_gemini_transient_statuses_are_sanitized(status: int) -> None:
    provider = GeminiEmbeddingProvider(
        api_key="synthetic-secret",
        model="gemini-embedding-001",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status)
        ),
    )

    with pytest.raises(TransientProviderError) as error:
        await provider.embed(["synthetic text"])

    assert "synthetic-secret" not in str(error.value)


# Verify provider selection follows deterministic and approved settings.
def test_embedding_provider_builder() -> None:
    provider = build_embedding_provider(Settings(generation_provider="fake"))
    assert provider.name == "fake"

    provider = build_embedding_provider(
        Settings(
            generation_provider="gemini",
            embedding_provider="fake",
        )
    )
    assert provider.name == "fake"

    with pytest.raises(ProviderError, match="Ollama"):
        build_embedding_provider(
            Settings(
                generation_provider="ollama",
                embedding_provider="ollama",
            )
        )

    with pytest.raises(ProviderError, match="no-training"):
        build_embedding_provider(
            Settings(
                generation_provider="gemini",
                embedding_provider="gemini",
            )
        )


# Verify configured Gemini embedding settings reach the provider unchanged.
def test_gemini_builder_keeps_embedding_settings() -> None:
    provider = build_embedding_provider(
        Settings(
            _env_file=None,
            generation_provider="gemini",
            embedding_provider="gemini",
            gemini_api_key="synthetic-key",
            gemini_no_training_acknowledged=True,
        )
    )

    assert isinstance(provider, GeminiEmbeddingProvider)
    assert provider.model == "gemini-embedding-001"
