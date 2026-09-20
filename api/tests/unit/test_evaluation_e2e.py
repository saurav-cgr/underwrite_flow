"""Unit coverage for the standalone public-HTTP evaluation runner.

`scripts/evaluate_e2e.py` is not part of the API package, so it is reached
the same way `scripts/pilot_load_probe.py` reaches `scripts/smoke.py`: by
path, not by install. These tests mock every HTTP call through
`httpx.MockTransport`, so no real Compose stack is required.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

# Skip this whole module, rather than block collection of every other test,
# until T047 adds the runner script this file exercises.
evaluate_e2e = pytest.importorskip("evaluate_e2e")
EvaluationFailure = evaluate_e2e.EvaluationFailure
atomic_write_json = evaluate_e2e.atomic_write_json
exit_code_for = evaluate_e2e.exit_code_for
login = evaluate_e2e.login
run_case = evaluate_e2e.run_case
sanitized_failure = evaluate_e2e.sanitized_failure

RECORD = {
    "case_id": "synthetic-motor-001",
    "product_code": "motor-private-car",
    "journey_type": "new_business",
    "expected": {"route": "expedited"},
    "workflow_input": {
        "payload": {"vehicle_age": 4, "vehicle_use": "personal"},
    },
    "documents": [
        {
            "document_id": "identity_record",
            "filename": "identity.pdf",
            "lines": ["vehicle_age: 4"],
        },
    ],
}


# Build a mocked client that answers every request with a fixed response map.
def mocked_client(responses: dict[str, httpx.Response]) -> httpx.Client:
    # Route each mocked request by its method and path, ignoring the body.
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key not in responses:
            raise AssertionError(f"unexpected request: {key}")
        return responses[key]

    return httpx.Client(
        base_url="http://evaluation-api/api/v1",
        transport=httpx.MockTransport(handler),
    )


# Verify login parses the access token into a bearer authorization header.
def test_login_returns_bearer_header_from_mocked_response() -> None:
    client = mocked_client(
        {
            "POST /api/v1/auth/login": httpx.Response(
                200, json={"access_token": "synthetic-token"}
            ),
        }
    )

    headers = login(client, "applicant")

    assert headers == {"Authorization": "Bearer synthetic-token"}


# Verify one case reports its route the same way across repeated mocked runs.
def test_run_case_reports_a_stable_route_from_a_mocked_http_flow() -> None:
    responses = {
        "POST /api/v1/cases": httpx.Response(
            200, json={"id": "11111111-1111-1111-1111-111111111111"}
        ),
        "POST /api/v1/cases/11111111-1111-1111-1111-111111111111/documents":
            httpx.Response(200, json={"document_id": "identity_record"}),
        "POST /api/v1/cases/11111111-1111-1111-1111-111111111111/submit":
            httpx.Response(
                200,
                json={"recommendation": {"route": "expedited", "factors": []}},
            ),
    }
    applicant = {"Authorization": "Bearer synthetic-applicant"}

    first = run_case(mocked_client(responses), applicant, RECORD)
    second = run_case(mocked_client(responses), applicant, RECORD)

    assert first == second == {
        "case_id": "synthetic-motor-001",
        "route": "expedited",
    }


# Verify a route mismatch raises a case-level failure instead of an assert.
def test_run_case_raises_a_sanitized_failure_on_route_mismatch() -> None:
    responses = {
        "POST /api/v1/cases": httpx.Response(
            200, json={"id": "11111111-1111-1111-1111-111111111111"}
        ),
        "POST /api/v1/cases/11111111-1111-1111-1111-111111111111/documents":
            httpx.Response(200, json={"document_id": "identity_record"}),
        "POST /api/v1/cases/11111111-1111-1111-1111-111111111111/submit":
            httpx.Response(
                200,
                json={"recommendation": {"route": "standard", "factors": []}},
            ),
    }
    applicant = {"Authorization": "Bearer synthetic-applicant"}

    with pytest.raises(EvaluationFailure) as excinfo:
        run_case(mocked_client(responses), applicant, RECORD)

    assert excinfo.value.detail == {
        "case_id": "synthetic-motor-001",
        "stage": "submit",
        "code": "unexpected_route",
    }


# Verify a failure record carries only the case ID, stage, and code.
def test_sanitized_failure_contains_only_safe_fields() -> None:
    failure = sanitized_failure("synthetic-motor-001", "submit", "http_error")

    assert failure == {
        "case_id": "synthetic-motor-001",
        "stage": "submit",
        "code": "http_error",
    }
    assert set(failure) == {"case_id", "stage", "code"}


# Verify the result artifact is written whole, never as a partial file.
def test_atomic_write_json_leaves_no_partial_file_behind(
    tmp_path: Path,
) -> None:
    target = tmp_path / "results" / "e2e.json"
    payload = {"schema_version": 1, "passed": True}

    atomic_write_json(target, payload)

    assert json.loads(target.read_text()) == payload
    assert list(target.parent.glob("*.tmp")) == []


# Verify a passing result exits zero and a failing result exits nonzero.
def test_exit_code_matches_the_passed_flag() -> None:
    assert exit_code_for({"passed": True}) == 0
    assert exit_code_for({"passed": False}) == 1


# Verify an unexpected HTTP/runtime failure still writes a sanitized result.
def test_main_sanitizes_an_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(base_url: str) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(evaluate_e2e, "run_evaluation", boom)
    result_path = tmp_path / "e2e.json"
    monkeypatch.setattr(evaluate_e2e, "RESULT_PATH", result_path)

    exit_code = evaluate_e2e.main()

    assert exit_code == 1
    written = json.loads(result_path.read_text())
    assert written["passed"] is False
    assert written["failures"] == [
        {"case_id": "dataset", "stage": "runtime", "code": "ConnectError"}
    ]
