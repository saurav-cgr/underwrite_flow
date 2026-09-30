"""Route explanation fallback and citation safety tests."""

import json

import httpx
import pytest

from underwriteflow.providers.guidance import (
    GuidanceCitation,
    GuidanceOutput,
    GeminiGuidanceProvider,
)
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
)
from underwriteflow.workflow.explain import explain_route
from underwriteflow.knowledge.explainer import RouteExplainer


class DummySession:
    """Capture audit events without requiring a database connection."""

    # Retain one event added by the explainer.
    def __init__(self) -> None:
        self.events: list[object] = []

    # Capture an audit event for later assertions.
    def add(self, event: object) -> None:
        self.events.append(event)

    # Provide a no-op savepoint context manager.
    def begin_nested(self) -> "DummySession":
        return self

    # Enter the no-op savepoint.
    async def __aenter__(self) -> "DummySession":
        return self

    # Leave the no-op savepoint without suppressing errors.
    async def __aexit__(self, *args: object) -> None:
        del args


class FailingProvider:
    """Raise one sanitized provider failure."""

    name = "fake"
    model = "fake"

    # Simulate a provider failure after retrieval succeeds.
    async def explain(self, request: object) -> GuidanceOutput:
        del request
        raise ProviderError("synthetic provider failure")


class RetryingProvider:
    """Fail transiently before returning a valid guidance response."""

    name = "fake"
    model = "fake"

    # Fail requested attempts before returning a cited explanation.
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    # Count calls to prove retries stay bounded.
    async def explain(self, request: object) -> GuidanceOutput:
        del request
        self.calls += 1
        if self.calls <= self.failures:
            raise TransientProviderError("synthetic temporary failure")
        return GuidanceOutput(
            text="Standard review needs evidence.",
            citations=[
                GuidanceCitation(
                    version="g1",
                    passage_key="high-cover-standard",
                )
            ],
        )


class InvalidCitationProvider:
    """Return a citation not present in retrieved passages."""

    name = "fake"
    model = "fake"

    # Simulate untrusted provider output for citation filtering.
    async def explain(self, request: object) -> GuidanceOutput:
        del request
        return GuidanceOutput(
            text="Standard review needs evidence.",
            citations=[
                GuidanceCitation(
                    version="g1",
                    passage_key="missing-key",
                )
            ],
        )


class OmittingMissingItemProvider:
    """Return a valid top-level citation but omit required missing items."""

    name = "fake"
    model = "fake"

    # Simulate a provider that forgets one requested missing item.
    async def explain(self, request: object) -> GuidanceOutput:
        del request
        return GuidanceOutput(
            text="Standard review needs evidence.",
            citations=[
                GuidanceCitation(
                    version="g1",
                    passage_key="high-cover-standard",
                )
            ],
            missing_items=[],
        )


# Build a route state with a pinned version and one retrieved passage.
def route_state() -> dict[str, object]:
    return {
        "case_id": "case-id",
        "recommendation": {
            "route": "standard",
            "factors": ["standard_rule"],
        },
        "missing_information": ["income_record"],
        "guidance_context": {
            "case_id": "case-id",
            "product_code": "life-individual-term",
            "age": 36,
            "sum_assured": 10_000_000,
            "guideline_version_id": "version-id",
            "regulation_version_id": None,
        },
    }


# Return one deterministic passage for explainer unit tests.
def retrieved_passages() -> list[dict[str, object]]:
    return [
        {
            "version": "g1",
            "version_id": "version-id",
            "passage_key": "high-cover-standard",
            "title": "High cover review",
            "body": "Synthetic guidance body.",
        }
    ]


# Verify provider failure produces a cited deterministic template.
@pytest.mark.asyncio
async def test_provider_error_uses_template_without_changing_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep retrieval deterministic and isolated from PostgreSQL.
    # Keep retrieval deterministic while testing Gemini citation filtering.
    async def fake_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        return retrieved_passages()

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", fake_retrieve
    )
    state = route_state()
    result = await explain_route(
        state,
        RouteExplainer(DummySession(), FailingProvider(), object()),
    )

    assert result["route_explanation"]["status"] == "template"
    assert result["route_explanation"]["citations"][0]["passage_key"] == (
        "high-cover-standard"
    )
    assert state["recommendation"] == {
        "route": "standard",
        "factors": ["standard_rule"],
    }


# Verify transient guidance failures retry only within the explanation branch.
@pytest.mark.asyncio
async def test_transient_provider_error_retries_before_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep retrieval deterministic and isolated from PostgreSQL.
    async def fake_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        return retrieved_passages()

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", fake_retrieve
    )
    provider = RetryingProvider(failures=2)
    state = route_state()
    state["missing_information"] = []
    result = await explain_route(
        state,
        RouteExplainer(DummySession(), provider, object(), 2),
    )

    assert provider.calls == 3
    assert result["route_explanation"]["status"] == "generated"


# Verify retrieval errors produce the explicit unavailable state.
@pytest.mark.asyncio
async def test_retrieval_error_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Simulate a database or embedding failure.
    async def broken_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        raise ProviderError("synthetic retrieval failure")

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", broken_retrieve
    )
    result = await explain_route(
        route_state(),
        RouteExplainer(DummySession(), FailingProvider(), object()),
    )

    assert result["route_explanation"] == {
        "status": "unavailable",
        "text": "Explanation unavailable.",
        "missing_items": [],
        "citations": [],
        "provider": None,
        "model": None,
        "request_hash": None,
    }
    assert "ProviderError" in caplog.text
    assert "synthetic retrieval failure" not in caplog.text


# Verify no pin and manual routes produce no explanation node output.
@pytest.mark.asyncio
async def test_no_pin_and_manual_route_produce_no_explanation() -> None:
    no_pin = route_state()
    no_pin["guidance_context"] = {}
    assert await explain_route(
        no_pin,
        RouteExplainer(DummySession(), FailingProvider(), object()),
    ) == {}

    manual = route_state()
    manual["recommendation"] = {"route": "manual", "factors": []}
    assert await explain_route(
        manual,
        RouteExplainer(DummySession(), FailingProvider(), object()),
    ) == {}


# Verify invalid citations are dropped and recorded without route mutation.
@pytest.mark.asyncio
async def test_invalid_citation_is_dropped_and_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Return one valid passage while provider returns an invalid key.
    async def fake_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        return retrieved_passages()

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", fake_retrieve
    )
    session = DummySession()
    state = route_state()
    result = await explain_route(
        state,
        RouteExplainer(session, InvalidCitationProvider(), object()),
    )

    assert result["route_explanation"]["status"] == "template"
    assert state["recommendation"]["route"] == "standard"
    assert session.events[0].event_type == "citation_dropped"
    assert session.events[0].details["case_id"] == "case-id"


# Verify an adapter response with an unknown citation is audited and templated.
@pytest.mark.asyncio
async def test_gemini_invalid_citation_is_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Return one Gemini response with a citation outside retrieved passages.
    def handler(request: httpx.Request) -> httpx.Response:
        del request
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
                                            "text": "Standard review.",
                                            "citations": [
                                                {
                                                    "version": "g1",
                                                    "passage_key": "missing",
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

    # Keep retrieval deterministic while testing Gemini citation filtering.
    async def fake_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        return retrieved_passages()

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", fake_retrieve
    )
    session = DummySession()
    provider = GeminiGuidanceProvider(
        api_key="synthetic-key",
        model="synthetic-model",
        transport=httpx.MockTransport(handler),
    )

    result = await explain_route(
        route_state(), RouteExplainer(session, provider, object())
    )

    assert result["route_explanation"]["status"] == "template"
    assert session.events[0].event_type == "citation_dropped"


# Verify omitted missing items force the deterministic cited template.
@pytest.mark.asyncio
async def test_missing_item_omission_uses_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep retrieval deterministic and isolated from PostgreSQL.
    async def fake_retrieve(*args: object, **kwargs: object) -> list[dict]:
        del args, kwargs
        return retrieved_passages()

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", fake_retrieve
    )
    result = await explain_route(
        route_state(),
        RouteExplainer(DummySession(), OmittingMissingItemProvider(), object()),
    )

    explanation = result["route_explanation"]
    assert explanation["status"] == "template"
    assert explanation["missing_items"][0]["item"] == "income_record"
    assert explanation["missing_items"][0]["citations"]
