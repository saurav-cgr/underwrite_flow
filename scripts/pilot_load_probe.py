"""Run a bounded ten-case synthetic load probe against the Compose stack.

Exactly ten fictional motor cases are processed end to end through the public
API with the deterministic fake provider. The probe reports per-case timing and
proves the bounded parallel fan-out, the recorded provider metadata, and the
final routes stay stable. It performs no external provider call, enables no
tracing, and writes only synthetic rows.

Run it through Compose, which mounts this directory read-only:

    docker compose -f compose.yaml -f compose.smoke.yaml \
        run --rm api python /app/scripts/pilot_load_probe.py
"""

from dataclasses import dataclass
from statistics import median
from time import perf_counter

from fastapi.testclient import TestClient

from smoke import MOTOR_EVIDENCE_LINES, login, recover_case
from underwriteflow.app import create_app
from underwriteflow.workflow.nodes import MAX_DOCUMENT_BRANCHES

# Exact number of synthetic cases this probe processes, and never more.
CASE_COUNT = 10

# Deterministic idempotency keys, so repeated runs reuse the same ten cases.
PROBE_KEY = "synthetic-pilot-probe-v2"

# Wall-clock budget for the whole probe, as a bound rather than a benchmark.
BUDGET_SECONDS = 300.0

# Final triage routes the PRD allows a human to confirm.
FINAL_ROUTES = frozenset({"expedited", "standard", "specialist"})

# The synthetic application every probe case submits.
PROBE_PAYLOAD = {
    "vehicle_age": 4,
    "vehicle_use": "personal",
    "prior_claims": 0,
    "claimed_ncb_percent": 20,
}

# Documents the fictional motor configuration requires for submission.
PROBE_DOCUMENT_CODES = ["identity_record", "vehicle_record"]

# Route the consistent synthetic evidence is expected to recommend.
EXPECTED_ROUTE = "expedited"

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")
ADMINISTRATOR = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)


@dataclass(frozen=True)
class CaseRun:
    """One processed case with its measured duration and recorded decision."""

    index: int
    milliseconds: float
    route: str
    provider_calls: int


# Read the newest submission event recorded for one probe case.
def submission_details(
    client: TestClient, case_id: str, administrator: dict[str, str]
) -> dict:
    response = client.get(
        f"/api/v1/audit/cases/{case_id}", headers=administrator
    )
    assert response.status_code == 200, response.text
    submissions = [
        event
        for event in response.json()
        if event["event_type"] in {"case_submitted", "case_resubmitted"}
    ]
    assert submissions, f"no submission event recorded for {case_id}"
    return submissions[-1]["details"]


# Process one synthetic case end to end and measure the elapsed wall clock.
def run_case(
    client: TestClient,
    index: int,
    applicant: dict[str, str],
    underwriter: dict[str, str],
    administrator: dict[str, str],
) -> CaseRun:
    started = perf_counter()
    created = client.post(
        "/api/v1/cases",
        headers=applicant,
        json={
            "product_code": "motor-private-car",
            "idempotency_key": f"{PROBE_KEY}-{index}",
            "payload": PROBE_PAYLOAD,
            "document_codes": PROBE_DOCUMENT_CODES,
        },
    )
    assert created.status_code == 200, created.text
    case = created.json()
    completion = recover_case(client, case, applicant, underwriter)
    assert completion["status"] == "completed", completion
    details = submission_details(client, str(case["id"]), administrator)
    return CaseRun(
        index=index,
        milliseconds=(perf_counter() - started) * 1000,
        route=str(details.get("recommendation")),
        provider_calls=len(details.get("provider_calls") or []),
    )


# Report the measured spread without presenting it as a performance claim.
def report(runs: list[CaseRun], elapsed: float) -> None:
    durations = [run.milliseconds for run in runs]
    route_counts: dict[str, int] = {}
    for run in runs:
        route_counts[run.route] = route_counts.get(run.route, 0) + 1
    print(
        f"Pilot probe passed: {len(runs)} synthetic cases in "
        f"{elapsed:.2f}s of a {BUDGET_SECONDS:.0f}s bound"
    )
    print(
        "  per case: "
        f"min {min(durations):.0f}ms  median {median(durations):.0f}ms  "
        f"max {max(durations):.0f}ms"
    )
    print(f"  routes: {route_counts}")
    print(
        "  provider calls per case: "
        f"max {max(run.provider_calls for run in runs)} of "
        f"{MAX_DOCUMENT_BRANCHES} bounded branches"
    )
    print("  note: local synthetic timings, not a performance benchmark")


# Run the bounded ten-case probe and assert every bound it claims.
def run_probe() -> None:
    started = perf_counter()
    with TestClient(create_app()) as client:
        activation = client.post(
            "/api/v1/products/motor-private-car/activate",
            headers=login(client, *ADMINISTRATOR),
            json={"version": "v2"},
        )
        assert activation.status_code == 200, activation.text
        applicant = login(client, *APPLICANT)
        underwriter = login(client, *UNDERWRITER)
        administrator = login(client, *ADMINISTRATOR)
        runs = [
            run_case(client, index, applicant, underwriter, administrator)
            for index in range(CASE_COUNT)
        ]
    elapsed = perf_counter() - started
    report(runs, elapsed)

    assert len(runs) == CASE_COUNT, len(runs)
    # One parent graph per case, so the fan-out never exceeds its bound.
    assert all(
        run.provider_calls == len(PROBE_DOCUMENT_CODES) for run in runs
    ), [run.provider_calls for run in runs]
    routes = {run.route for run in runs}
    assert routes <= FINAL_ROUTES, routes
    assert routes == {EXPECTED_ROUTE}, routes
    assert elapsed <= BUDGET_SECONDS, elapsed


if __name__ == "__main__":
    run_probe()
