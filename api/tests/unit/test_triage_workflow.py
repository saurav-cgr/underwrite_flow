import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError
from types import SimpleNamespace
from uuid import uuid4

from fixtures.auth import session_for
from fixtures.records import synthetic_user

from underwriteflow.app import create_app
from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.cases.submission import SubmissionService
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import (
    build_triage_graph,
    has_low_confidence,
    resolve_final_route,
)
from underwriteflow.reviews.schemas import ReviewCommand


# Verify cautious deterministic signals outrank standard and expedited routes.
@pytest.mark.asyncio
async def test_triage_graph_applies_route_precedence_before_review() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-precedence")

    paused = await graph.ainvoke(
        {
            "case_id": "triage-precedence",
            "validations": [{"rule_code": "synthetic_standard", "status": "triggered", "route": "standard"}],
            "risk_signals": [{"code": "synthetic_signal", "severity": "high"}],
            "conflicts": [],
            "missing_information": [],
            "evidence": [{"field_name": "synthetic_field", "value": "stored", "source_locator": "line:1"}],
        },
        config=config,
    )

    assert paused["recommendation"]["route"] == "specialist"
    assert paused["summary"]["evidence"][0]["source_locator"] == "line:1"

    resumed = await graph.ainvoke(
        Command(resume={"action": "confirm", "evidence_acknowledged": True}),
        config=config,
    )

    assert resumed["final_route"] == "specialist"
    assert resumed["review_status"] == "confirmed"


# Verify override commands require a reason and select the underwriter route.
@pytest.mark.asyncio
async def test_triage_graph_requires_override_reason() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-override")
    await graph.ainvoke(
        {
            "case_id": "triage-override",
            "validations": [],
            "risk_signals": [],
            "conflicts": [],
            "missing_information": [],
            "evidence": [],
        },
        config=config,
    )

    with pytest.raises(ValueError, match="override reason is required"):
        await graph.ainvoke(
            Command(
                resume={
                    "action": "override",
                    "selected_route": "standard",
                    "evidence_acknowledged": True,
                }
            ),
            config=config,
        )


# Verify requesting information pauses completion without creating a final route.
@pytest.mark.asyncio
async def test_triage_graph_supports_information_request() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-information")
    paused = await graph.ainvoke(
        {
            "case_id": "triage-information",
            "validations": [],
            "risk_signals": [],
            "conflicts": [],
            "missing_information": ["synthetic_document"],
            "evidence": [],
        },
        config=config,
    )

    assert paused["recommendation"]["route"] == "needs_information"
    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "request_information",
                "reason": "Synthetic document required",
                "evidence_acknowledged": True,
            }
        ),
        config=config,
    )

    assert resumed["final_route"] is None
    assert resumed["review_status"] == "needs_information"


# Verify review commands reject an override without its mandatory reason.
def test_review_command_requires_override_reason() -> None:
    with pytest.raises(ValidationError, match="override reason is required"):
        ReviewCommand(
            action="override",
            selected_route="standard",
            evidence_acknowledged=True,
        )


# Verify a decision is refused until the evidence is acknowledged.
def test_review_command_requires_evidence_acknowledgement() -> None:
    with pytest.raises(ValidationError, match="evidence acknowledgement"):
        ReviewCommand(action="confirm")


# Verify whitespace-only reasons are treated as missing text.
def test_review_command_rejects_whitespace_only_reason() -> None:
    with pytest.raises(ValidationError, match="override reason is required"):
        ReviewCommand(
            action="override",
            selected_route="standard",
            reason="   ",
            evidence_acknowledged=True,
        )


# Verify a specialist route requires one configured specialist label.
def test_review_command_requires_specialist_label() -> None:
    with pytest.raises(ValidationError, match="specialist label is required"):
        ReviewCommand(
            action="override",
            selected_route="specialist",
            reason="Synthetic specialist reason",
            evidence_acknowledged=True,
        )


# Verify internal product routes cannot be selected as final override routes.
def test_review_command_rejects_internal_override_routes() -> None:
    with pytest.raises(ValidationError):
        ReviewCommand(
            action="override",
            selected_route="manual",
            reason="Synthetic reason",
            evidence_acknowledged=True,
        )


# Verify configured manual and information rules outrank specialist and expedited routes.
@pytest.mark.parametrize(
    ("route", "expected"),
    [("manual", "manual"), ("needs_information", "needs_information")],
)
@pytest.mark.asyncio
async def test_triage_graph_honors_internal_rule_routes(route: str, expected: str) -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    paused = await graph.ainvoke(
        {
            "case_id": f"triage-{route}",
            "validations": [{"status": "triggered", "route": route}],
            "risk_signals": [],
            "conflicts": [],
            "missing_information": [],
            "evidence": [],
        },
        config=thread_config(f"triage-{route}"),
    )

    assert paused["recommendation"]["route"] == expected


# Verify applicants cannot resume an underwriter review checkpoint.
def test_review_endpoint_requires_review_permission() -> None:
    app = create_app()

    with synthetic_user() as user_id:
        # Supply an existing applicant actor to the authorization dependency.
        async def applicant_session() -> dict[str, object]:
            return session_for("applicant", str(user_id))

        app.dependency_overrides[get_current_session] = applicant_session
        response = TestClient(app).post(
            f"/api/v1/reviews/{uuid4()}",
            json={"action": "confirm"},
        )

    assert response.status_code == 403


# Verify the shared resolver turns a manual recommendation into specialist.
def test_resolve_final_route_maps_manual_recommendation() -> None:
    command = ReviewCommand(action="confirm", evidence_acknowledged=True)

    # The status is overridden because the resolved route differs from the
    # recommended manual state, which is never a final route.
    assert resolve_final_route(command, "manual") == (
        "specialist",
        "overridden",
    )


# Verify the shared resolver keeps a confirmed specialist recommendation.
def test_resolve_final_route_confirms_specialist_recommendation() -> None:
    command = ReviewCommand(action="confirm", evidence_acknowledged=True)

    assert resolve_final_route(command, "specialist") == (
        "specialist",
        "confirmed",
    )


# Verify overriding an internal recommendation selects the requested route.
def test_resolve_final_route_overrides_internal_recommendation() -> None:
    command = ReviewCommand(
        action="override",
        selected_route="standard",
        reason="Synthetic override reason",
        evidence_acknowledged=True,
    )

    assert resolve_final_route(command, "manual") == ("standard", "overridden")


# Verify an information request never resolves to a final route.
def test_resolve_final_route_returns_no_route_for_information_request() -> None:
    command = ReviewCommand(
        action="request_information",
        reason="Synthetic information reason",
        evidence_acknowledged=True,
    )

    assert resolve_final_route(command, "specialist") == (
        None,
        "needs_information",
    )


# Verify confirming an information recommendation stays a queue state.
def test_resolve_final_route_confirms_information_recommendation() -> None:
    command = ReviewCommand(action="confirm", evidence_acknowledged=True)

    assert resolve_final_route(command, "needs_information") == (
        None,
        "needs_information",
    )


# Verify unknown confidence counts as low confidence rather than certainty.
def test_has_low_confidence_treats_unknown_confidence_as_low() -> None:
    assert has_low_confidence([{"confidence": None}]) is True
    assert has_low_confidence([{"field_name": "vehicle_age"}]) is True
    assert has_low_confidence([{"confidence": "unknown"}]) is True
    assert has_low_confidence([]) is False


# Verify a measured zero score is low and a confident field is not.
def test_has_low_confidence_uses_the_measured_score() -> None:
    assert has_low_confidence([{"confidence": 0.0}]) is True
    assert has_low_confidence([{"confidence": 0.79}]) is True
    assert has_low_confidence([{"confidence": 0.8}]) is False
    assert has_low_confidence([{"confidence": 1.0}]) is False


# Verify the triage input flags unknown confidence from reconciled evidence.
def test_build_triage_state_flags_unknown_confidence() -> None:
    service = SubmissionService(
        provider=FakeProvider(),
        upload_root="/tmp/synthetic-uploads",
        database_url="postgresql://synthetic",
    )
    case = SimpleNamespace(id=uuid4())

    unknown = service.build_triage_state(
        case,
        [],
        {"reconciled_fields": [{"field_name": "vehicle_age"}]},
        {},
        [],
    )
    confident = service.build_triage_state(
        case,
        [],
        {
            "reconciled_fields": [
                {"field_name": "vehicle_age", "confidence": 1.0}
            ]
        },
        {},
        [],
    )

    assert unknown["low_confidence"] is True
    assert confident["low_confidence"] is False


# Verify both extraction and branch failures reach the triage input.
def test_build_triage_state_records_processing_failures() -> None:
    service = SubmissionService(
        provider=FakeProvider(),
        upload_root="/tmp/synthetic-uploads",
        database_url="postgresql://synthetic",
    )
    case = SimpleNamespace(id=uuid4())

    state = service.build_triage_state(
        case,
        [],
        {
            "reconciled_fields": [],
            "results": [
                {
                    "document_id": "synthetic-branch",
                    "filename": "synthetic.pdf",
                    "fields": [],
                    "error_code": "provider_error",
                },
                {
                    "document_id": "synthetic-ok",
                    "filename": "ok.pdf",
                    "fields": [],
                    "error_code": None,
                },
            ],
        },
        {},
        [
            {
                "document_id": "synthetic-upload",
                "filename": "upload.pdf",
                "error_code": "extraction_failed",
            }
        ],
    )

    assert state["processing_failures"] == [
        {
            "document_id": "synthetic-upload",
            "filename": "upload.pdf",
            "error_code": "extraction_failed",
        },
        {
            "document_id": "synthetic-branch",
            "filename": "synthetic.pdf",
            "error_code": "provider_error",
        },
    ]


# Verify a document branch that produced no evidence routes to specialist.
@pytest.mark.asyncio
async def test_processing_failures_route_to_specialist_review() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-processing-failure")

    paused = await graph.ainvoke(
        {
            "case_id": "triage-processing-failure",
            "processing_failures": [
                {
                    "document_id": "synthetic-document",
                    "error_code": "provider_error",
                }
            ],
            "validations": [],
            "risk_signals": [],
            "conflicts": [],
            "missing_information": [],
            "evidence": [],
        },
        config=config,
    )

    assert paused["recommendation"]["route"] == "specialist"
    assert paused["recommendation"]["factors"] == ["processing_failure"]


# Verify a processing failure never outranks a request for information.
@pytest.mark.asyncio
async def test_processing_failures_do_not_outrank_missing_information() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-failure-precedence")

    paused = await graph.ainvoke(
        {
            "case_id": "triage-failure-precedence",
            "processing_failures": [{"error_code": "extraction_failed"}],
            "missing_information": ["prior_claims"],
            "validations": [],
            "risk_signals": [],
            "conflicts": [],
            "evidence": [],
        },
        config=config,
    )

    assert paused["recommendation"]["route"] == "needs_information"


# Verify an unsupported product configuration outranks every other signal and
# still resolves to a final route once a human reviews it.
@pytest.mark.asyncio
async def test_unsupported_product_recommends_manual_review() -> None:
    graph = build_triage_graph(checkpointer=MemorySaver())
    config = thread_config("triage-unsupported")

    paused = await graph.ainvoke(
        {
            "case_id": "triage-unsupported",
            "unsupported_product": True,
            "validations": [
                {"status": "triggered", "route": "standard"}
            ],
            "risk_signals": [{"code": "synthetic_signal"}],
            "conflicts": [{"field_name": "vehicle_age"}],
            "missing_information": ["prior_claims"],
            "evidence": [],
        },
        config=config,
    )

    assert paused["recommendation"]["route"] == "manual"
    assert paused["recommendation"]["factors"] == ["unsupported_product"]

    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "confirm",
                "specialist_label": "motor inspection",
                "evidence_acknowledged": True,
            }
        ),
        config=config,
    )

    assert resumed["final_route"] == "specialist"
    assert resumed["review_status"] == "overridden"
