"""Failure-path checks for triage state and routing."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from underwriteflow.cases.submission import SubmissionService
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph


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


# Verify unsupported product state outranks signals until human review.
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
