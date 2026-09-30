"""Deterministic and Gemini embedding providers."""

import hashlib
import math
from typing import Protocol

import httpx

from underwriteflow.config import Settings
from underwriteflow.providers.redaction import redact_personal_data
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
    is_transient_status,
)

EMBEDDING_HOST = "generativelanguage.googleapis.com"
EMBEDDING_DIMENSIONS = 768


class EmbeddingProvider(Protocol):
    """Application-owned contract for batch text embeddings."""

    name: str
    model: str

    # Embed each input text in stable input order.
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


# Normalize one vector to unit length for cosine comparisons.
def _unit(values: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in values))
    if length == 0:
        values[0] = 1.0
        return values
    return [value / length for value in values]


class FakeEmbeddingProvider:
    """Hash-based embedder with deterministic lexical similarity."""

    name = "fake"
    model = "fake-embedding-768"

    # Hash token contributions into a normalized fixed-width vector.
    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            values = [0.0] * EMBEDDING_DIMENSIONS
            tokens = text.casefold().split()
            for token in tokens or ["empty"]:
                digest = hashlib.sha256(token.encode()).digest()
                index = int.from_bytes(digest[:4], "big") % 768
                sign = 1.0 if digest[4] & 1 else -1.0
                values[index] += sign
            vectors.append(_unit(values))
        return vectors


class GeminiEmbeddingProvider:
    """Call Gemini batch embeddings with redacted synthetic text."""

    name = "gemini"

    # Configure Gemini embedding requests and optional test transport.
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 30,
        pii_redaction_terms: tuple[str, ...] = (),
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.pii_redaction_terms = pii_redaction_terms
        self.transport = transport

    # Request one Gemini batch and return validated 768-dimensional vectors.
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise ProviderError("Gemini embedding provider is not configured")
        safe_texts = [
            redact_personal_data(text, self.pii_redaction_terms)
            for text in texts
        ]
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": EMBEDDING_DIMENSIONS,
                }
                for text in safe_texts
            ]
        }
        url = (
            f"https://{EMBEDDING_HOST}/v1beta/models/"
            f"{self.model}:batchEmbedContents"
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                raw = response.json()["embeddings"]
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise TransientProviderError(
                "Gemini embedding provider is temporarily unavailable"
            ) from error
        except httpx.HTTPStatusError as error:
            if is_transient_status(error.response.status_code):
                raise TransientProviderError(
                    "Gemini embedding provider is temporarily unavailable"
                ) from error
            raise ProviderError("Gemini embedding provider failed") from error
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise ProviderError("Gemini embedding provider failed") from error
        vectors = [item["values"] for item in raw]
        if len(vectors) != len(texts):
            raise ProviderError(
                "Gemini embedding provider returned invalid data"
            )
        if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
            raise ProviderError(
                "Gemini embedding provider returned invalid data"
            )
        return [[float(value) for value in vector] for vector in vectors]


# Require the same host and no-training safeguards as Gemini generation.
def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider_name = settings.embedding_provider or settings.generation_provider
    if provider_name == "fake":
        return FakeEmbeddingProvider()
    if provider_name == "ollama":
        raise ProviderError(
            "Ollama embedding provider is not supported"
        )
    if not settings.gemini_no_training_acknowledged:
        raise ProviderError(
            "Gemini embedding provider requires a no-training project "
            "acknowledgement"
        )
    allowed = {host.lower() for host in settings.provider_allowed_hosts}
    if EMBEDDING_HOST.lower() not in allowed:
        raise ProviderError("Provider host is not approved")
    return GeminiEmbeddingProvider(
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        timeout_seconds=settings.provider_timeout_seconds,
        pii_redaction_terms=settings.pii_redaction_terms,
    )
