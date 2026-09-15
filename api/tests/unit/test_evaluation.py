import asyncio

import pytest
from fastapi.testclient import TestClient

from underwriteflow.app import create_app
from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.evaluation.dataset import load_dataset
from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.runner import run_evaluation
from underwriteflow.evaluation.tracing import redact_trace, trace_summary


# Verify the reference dataset has the planned synthetic split and balance.
def test_reference_dataset_has_balanced_synthetic_cases() -> None:
    records = load_dataset()

    assert len(records) == 90
    assert all(
        record["fixture_label"] == "SYNTHETIC - FOR DEMONSTRATION ONLY"
        for record in records
    )
    assert sum(record["split"] == "development" for record in records) == 60
    assert sum(record["split"] == "holdout" for record in records) == 30
    assert {
        product: sum(record["product_code"] == product for record in records)
        for product in {
            "motor-private-car",
            "life-individual-term",
            "health-individual-family-floater",
        }
    } == {
        "motor-private-car": 30,
        "life-individual-term": 30,
        "health-individual-family-floater": 30,
    }


# Verify evaluator reports route, detection, provenance, and workflow metrics.
def test_evaluator_reports_expected_metric_groups() -> None:
    records = [
        {
            "expected": {
                "route": "expedited",
                "evidence": ["identity_record"],
                "conflict": False,
                "missing": False,
                "unsupported_claims": 0,
            },
            "prediction": {
                "route": "expedited",
                "evidence": ["identity_record"],
                "conflict": False,
                "missing": False,
                "claim_count": 2,
                "unsupported_claims": 0,
            },
            "workflow_succeeded": True,
        },
        {
            "expected": {
                "route": "specialist",
                "evidence": ["identity_record"],
                "conflict": True,
                "missing": True,
                "unsupported_claims": 1,
            },
            "prediction": {
                "route": "standard",
                "evidence": [],
                "conflict": False,
                "missing": True,
                "claim_count": 2,
                "unsupported_claims": 2,
            },
            "workflow_succeeded": False,
        },
    ]

    summary = evaluate_records(records)

    assert summary["case_count"] == 2
    assert summary["route_agreement"] == 0.5
    assert summary["specialist_recall"] == 0.0
    assert summary["evidence_accuracy"] == 0.5
    assert summary["conflict_detection"] == 0.0
    assert summary["conflict_precision"] == 0.0
    assert summary["missing_data_detection"] == 1.0
    assert summary["missing_precision"] == 1.0
    assert summary["unsupported_claim_rate"] == 0.5
    assert summary["workflow_reliability"] == 0.5


# Verify a case the pipeline could not route is scored on missing information
# rather than counted as a route disagreement.
def test_unroutable_cases_leave_route_agreement_denominator() -> None:
    records = [
        {
            "expected": {
                "route": "specialist",
                "evidence": ["identity_record"],
                "conflict": False,
                "missing": True,
                "unsupported_claims": 0,
            },
            "prediction": {
                "route": "needs_information",
                "evidence": ["identity_record"],
                "conflict": False,
                "missing": True,
                "claim_count": 1,
                "unsupported_claims": 0,
            },
            "workflow_succeeded": True,
        }
    ]

    summary = evaluate_records(records)

    assert summary["routable_count"] == 0
    assert summary["needs_information_count"] == 1
    assert summary["route_agreement"] == 0.0
    assert summary["missing_data_detection"] == 1.0
    assert summary["missing_precision"] == 1.0


# Verify evaluation predictions come from deterministic workflow execution.
def test_runner_executes_fixture_workflows() -> None:
    summary = asyncio.run(run_evaluation("development"))

    assert summary["case_count"] == 60
    assert summary["workflow_reliability"] == 1.0
    # The reference set is solvable by design, so the pipeline must reproduce
    # every final-route label it had enough evidence to reach.
    assert summary["route_agreement"] == 1.0
    assert summary["routable_count"] + summary["needs_information_count"] == 60
    assert summary["conflict_detection"] == 1.0
    assert summary["missing_data_detection"] == 1.0
    assert all("prediction" not in record for record in load_dataset())


# Verify tracing removes secrets, identifiers, and raw document content.
def test_trace_redaction_keeps_only_safe_metadata() -> None:
    redacted = redact_trace(
        {
            "case_id": "synthetic-case-1",
            "document_text": "synthetic applicant document text",
            "prompt": "synthetic prompt",
            "output": {"route": "expedited"},
            "model": "synthetic-model",
        }
    )

    assert redacted == {
        "output": {"route": "expedited"},
        "model": "synthetic-model",
    }


# Verify opt-in tracing sends redacted output to the configured APAC endpoint.
def test_opt_in_trace_uses_apac_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    class RecordingClient:
        # Record the synthetic trace without making a network request.
        def __init__(self, **kwargs: str) -> None:
            calls["settings"] = kwargs

        # Record safe trace payloads for the APAC tracing smoke check.
        def create_run(self, **kwargs: object) -> None:
            calls["run"] = kwargs

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv(
        "LANGSMITH_ENDPOINT", "https://apac.api.smith.langchain.com"
    )
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setattr("langsmith.Client", RecordingClient)

    assert trace_summary({"case_id": "synthetic-case"}) is True
    assert calls["settings"] == {
        "api_url": "https://apac.api.smith.langchain.com",
        "api_key": None,
    }
    assert calls["run"] == {
        "name": "underwriteflow-synthetic-evaluation",
        "run_type": "chain",
        "inputs": {"dataset": "synthetic-evaluation"},
        "outputs": {},
        "project_name": "underwriteflow-local",
    }


# Verify evaluation results are visible only to administrators.
def test_evaluation_endpoint_is_administrator_only() -> None:
    app = create_app()

    # Supply a synthetic underwriter identity to the authorization dependency.
    async def underwriter_session() -> dict[str, str]:
        return {"sub": "synthetic-underwriter", "role": "Underwriter"}

    app.dependency_overrides[get_current_session] = underwriter_session
    response = TestClient(app).post("/api/v1/evaluation/run", json={})

    assert response.status_code == 403


# Verify administrators can run the full reference set on demand.
def test_administrator_can_run_full_evaluation() -> None:
    app = create_app()

    # Supply a synthetic administrator identity to the authorization dependency.
    async def administrator_session() -> dict[str, str]:
        return {"sub": "synthetic-administrator", "role": "Administrator"}

    app.dependency_overrides[get_current_session] = administrator_session
    response = TestClient(app).post("/api/v1/evaluation/run", json={})

    assert response.status_code == 200
    summary = response.json()
    assert summary["case_count"] == 90
    assert summary["split"] == "all"
    assert set(summary) >= {
        "route_agreement",
        "specialist_recall",
        "conflict_detection",
        "conflict_precision",
        "missing_data_detection",
        "missing_precision",
        "evidence_accuracy",
        "unsupported_claim_rate",
        "workflow_reliability",
        "routable_count",
        "needs_information_count",
        "trace_sent",
    }


# Verify the split selector narrows the run to the requested cases.
def test_evaluation_endpoint_accepts_a_known_split() -> None:
    app = create_app()

    # Supply a synthetic administrator identity to the authorization dependency.
    async def administrator_session() -> dict[str, str]:
        return {"sub": "synthetic-administrator", "role": "Administrator"}

    app.dependency_overrides[get_current_session] = administrator_session
    response = TestClient(app).post(
        "/api/v1/evaluation/run", json={"split": "holdout"}
    )

    assert response.status_code == 200
    assert response.json()["case_count"] == 30
    assert response.json()["split"] == "holdout"


# Verify an unknown split is rejected before any case is processed.
def test_evaluation_endpoint_rejects_an_unknown_split() -> None:
    app = create_app()

    # Supply a synthetic administrator identity to the authorization dependency.
    async def administrator_session() -> dict[str, str]:
        return {"sub": "synthetic-administrator", "role": "Administrator"}

    app.dependency_overrides[get_current_session] = administrator_session
    response = TestClient(app).post(
        "/api/v1/evaluation/run", json={"split": "everything"}
    )

    assert response.status_code == 422
