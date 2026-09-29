"""Guidance provider contracts and safe structured output."""

import json

import httpx
import pytest

from underwriteflow.config import Settings
from underwriteflow.providers.guidance import (
    FakeGuidanceProvider,
    GuidanceRequest,
    GeminiGuidanceProvider,
    build_guidance_provider,
)
from underwriteflow.providers.service import ProviderError


# Build one bounded request with a citable synthetic passage.
def guidance_request() -> GuidanceRequest:
    return GuidanceRequest(
        route="standard",
        factors=["standard_rule"],
        missing_items=[],
        context={"sum_assured": 10_000_000},
        passages=[
            {
                "version": "g1",
                "version_id": "version-id",
                "passage_key": "life-cover-high-sum-assured",
                "title": "High cover review",
                "body": "Synthetic high cover guidance.",
            }
        ],
    )


# Verify fake guidance stays deterministic and cites retrieved material.
@pytest.mark.asyncio
async def test_fake_guidance_is_deterministic() -> None:
    request = guidance_request()
    provider = FakeGuidanceProvider()

    first = await provider.explain(request)
    second = await provider.explain(request)

    assert first == second
    assert first.citations[0].passage_key == "life-cover-high-sum-assured"
    assert len(first.text.split()) <= 120


# Verify unsafe output length is rejected before persistence.
@pytest.mark.asyncio
async def test_guidance_output_rejects_long_text() -> None:
    request = guidance_request()
    long_text = " ".join(["word"] * 121)

    with pytest.raises(ProviderError, match="120 words"):
        await FakeGuidanceProvider(
            text=long_text
        ).explain(request)



# Verify unknown citations survive parsing for explainer-side audit.
@pytest.mark.asyncio
async def test_guidance_output_preserves_unknown_citation() -> None:
    result = await FakeGuidanceProvider(
        citation_key="missing-passage"
    ).explain(guidance_request())

    assert result.citations[0].passage_key == "missing-passage"


# Verify Gemini uses JSON mode, marks case data untrusted, and redacts it.
@pytest.mark.asyncio
async def test_gemini_guidance_request_is_safe() -> None:
    requests: list[httpx.Request] = []

    # Capture the remote request and return one valid structured explanation.
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "text": "Standard review. See "
                                            "high cover guidance.",
                                            "citations": [
                                                {
                                                    "version": "g1",
                                                    "passage_key": (
                                                        "life-cover-high-"
                                                        "sum-assured"
                                                    ),
                                                }
                                            ],
                                            "missing_items": [],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    request = guidance_request().model_copy(
        update={"context": {"applicant": "Synthetic Person"}}
    )
    provider = GeminiGuidanceProvider(
        api_key="synthetic-secret",
        model="synthetic-model",
        pii_redaction_terms=("Synthetic Person",),
        transport=httpx.MockTransport(handler),
    )

    result = await provider.explain(request)

    assert result.provider == "gemini"
    assert requests[0].url.host == "generativelanguage.googleapis.com"
    assert requests[0].url.path.endswith(":generateContent")
    payload = json.loads(requests[0].content)
    assert payload["generationConfig"]["responseMimeType"] == (
        "application/json"
    )
    assert "untrusted" in payload["systemInstruction"]["parts"][0]["text"]
    assert "Synthetic Person" not in requests[0].content.decode()
    assert "synthetic-secret" not in str(result)


# Verify guidance builder follows fake and approved Gemini settings.
def test_guidance_provider_builder() -> None:
    assert build_guidance_provider(
        Settings(generation_provider="fake")
    ).name == "fake"

    provider = build_guidance_provider(
        Settings(
            generation_provider="gemini",
            gemini_api_key="synthetic-key",
            gemini_no_training_acknowledged=True,
        )
    )
    assert provider.name == "gemini"


# Verify unsupported local guidance does not block case submission.
def test_ollama_guidance_provider_is_optional() -> None:
    assert build_guidance_provider(
        Settings(generation_provider="ollama")
    ) is None
