import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError
from uuid import uuid4

from underwriteflow.app import create_app
from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph
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

    # Supply a synthetic applicant identity without opening the database.
    async def applicant_session() -> dict[str, str]:
        return {"sub": str(uuid4()), "role": "Applicant"}

    app.dependency_overrides[get_current_session] = applicant_session
    response = TestClient(app).post(
        f"/api/v1/reviews/{uuid4()}",
        json={"action": "confirm"},
    )

    assert response.status_code == 403
