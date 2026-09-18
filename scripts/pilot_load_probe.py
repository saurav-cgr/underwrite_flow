"""Measure fresh bounded synthetic pilot cohorts through the public API.

The probe uses only fictional data and the deterministic fake provider. Its
local timings are evidence for the pilot decision, not capacity claims.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, Thread
from time import perf_counter
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from pilot_probe_metrics import (
    OCR_SAMPLES,
    CohortRun,
    MeasuredFakeProvider,
    measure_ocr_seconds_per_page,
    percentile,
    sample_pool,
    storage_metrics,
)
from smoke import login, text_pdf
from underwriteflow.app import create_app
from underwriteflow.workflow.nodes import MAX_DOCUMENT_BRANCHES

COHORT_SIZES = (10, 100)
MAX_WORKERS = 10
BUDGET_SECONDS = 300.0
EXPECTED_ROUTE = "expedited"
PRODUCT_VERSION = "v3"
QUEUE_SAMPLES = 20

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = (
    "underwriter@synthetic.test",
    "underwriteflow-demo-underwriter",
)
ADMINISTRATOR = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)

PROBE_PAYLOAD = {
    "vehicle_age": 4,
    "vehicle_use": "personal",
    "prior_claims": 0,
    "claimed_ncb_percent": 20,
    "policy_start_date": "2026-01-15",
}
PROBE_DOCUMENTS = (
    ("identity_record", "identity.pdf", ["synthetic_identity: DEMO-001"]),
    (
        "vehicle_record",
        "vehicle.pdf",
        [
            "vehicle_age: 4",
            "vehicle_use: personal",
            "prior_claims: 0",
            "claimed_ncb_percent: 20",
            "policy_start_date: 2026-01-15",
            "chassis_number: DEMOCHASSIS123",
            "engine_number: DEMOENGINE123",
            "registration_number: DEMO01AB1234",
            "ncb_percent: 0",
            "policy_expiry: 2026-01-05",
        ],
    ),
    (
        "registration_certificate",
        "registration.pdf",
        [
            "chassis_number: DEMOCHASSIS123",
            "engine_number: DEMOENGINE123",
            "registration_number: DEMO01AB1234",
        ],
    ),
)


@dataclass(frozen=True)
class CaseRun:
    """Measurements and result for one fresh synthetic case."""

    case_id: UUID
    ordinary_ms: tuple[float, ...]
    review_ready_ms: float
    route: str
    provider_calls: int


# Build a unique key from the invocation, cohort, and case index.
def fresh_case_key(run_id: str, cohort_size: int, index: int) -> str:
    return f"synthetic-probe-{run_id}-{cohort_size}-{index}"


# Time one ordinary API interaction and retain its response.
def measured_call(samples: list[float], call, *args, **kwargs):
    started = perf_counter()
    response = call(*args, **kwargs)
    samples.append((perf_counter() - started) * 1000)
    return response


# Read the provider-call count from the immutable submission audit event.
def provider_call_count(
    client: TestClient, case_id: UUID, administrator: dict[str, str]
) -> int:
    response = client.get(
        f"/api/v1/audit/cases/{case_id}",
        headers=administrator,
    )
    assert response.status_code == 200, response.text
    events = [
        event
        for event in response.json()
        if event["event_type"] == "case_submitted"
    ]
    assert events, case_id
    return len(events[-1]["details"].get("provider_calls") or [])


# Create, submit, review, and complete one fresh fictional motor case.
def run_case(
    client: TestClient,
    run_id: str,
    cohort_size: int,
    index: int,
    applicant: dict[str, str],
    underwriter: dict[str, str],
    administrator: dict[str, str],
) -> CaseRun:
    started = perf_counter()
    ordinary: list[float] = []
    created = measured_call(
        ordinary,
        client.post,
        "/api/v1/cases",
        headers=applicant,
        json={
            "product_code": "motor-private-car",
            "idempotency_key": fresh_case_key(
                run_id, cohort_size, index
            ),
            "payload": PROBE_PAYLOAD,
            "document_codes": [item[0] for item in PROBE_DOCUMENTS],
        },
    )
    assert created.status_code == 200, created.text
    case_id = UUID(created.json()["id"])
    for code, filename, lines in PROBE_DOCUMENTS:
        uploaded = measured_call(
            ordinary,
            client.post,
            f"/api/v1/cases/{case_id}/documents",
            headers=applicant,
            files={
                "document": (
                    filename,
                    text_pdf(lines),
                    "application/pdf",
                )
            },
            data={"document_code": code},
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = client.post(
        f"/api/v1/cases/{case_id}/submit",
        headers=applicant,
    )
    assert submitted.status_code == 200, submitted.text
    route = str(submitted.json()["recommendation"]["route"])
    assert route == EXPECTED_ROUTE, submitted.text
    review_ready_ms = (perf_counter() - started) * 1000
    reviewed = measured_call(
        ordinary,
        client.post,
        f"/api/v1/reviews/{case_id}",
        headers=underwriter,
        json={"action": "confirm", "evidence_acknowledged": True},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "confirmed", reviewed.text
    completed = measured_call(
        ordinary,
        client.post,
        f"/api/v1/completion/{case_id}",
        headers=underwriter,
    )
    assert completed.status_code == 200, completed.text
    return CaseRun(
        case_id=case_id,
        ordinary_ms=tuple(ordinary),
        review_ready_ms=review_ready_ms,
        route=route,
        provider_calls=provider_call_count(
            client, case_id, administrator
        ),
    )


# Measure the completed-queue endpoint after the cohort is committed.
def queue_p95(
    client: TestClient, underwriter: dict[str, str]
) -> float:
    durations: list[float] = []
    for _ in range(QUEUE_SAMPLES):
        response = measured_call(
            durations,
            client.get,
            "/api/v1/queues?status=completed",
            headers=underwriter,
        )
        assert response.status_code == 200, response.text
    return percentile(durations, 95)


# Run one fresh cohort with at most ten cases processing concurrently.
def run_cohort(
    client: TestClient,
    run_id: str,
    size: int,
    applicant: dict[str, str],
    underwriter: dict[str, str],
    administrator: dict[str, str],
    provider: MeasuredFakeProvider,
) -> CohortRun:
    provider.reset()
    pool = client.app.state.database.engine.pool
    pool_samples: list[int] = []
    stop = Event()
    sampler = Thread(
        target=sample_pool,
        args=(stop, pool, pool_samples),
        daemon=True,
    )
    started = perf_counter()
    sampler.start()
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            runs = list(
                executor.map(
                    lambda index: run_case(
                        client,
                        run_id,
                        size,
                        index,
                        applicant,
                        underwriter,
                        administrator,
                    ),
                    range(size),
                )
            )
    finally:
        stop.set()
        sampler.join()
    elapsed = perf_counter() - started
    provider_durations, max_active = provider.snapshot()
    case_ids = [run.case_id for run in runs]
    stored, uploads, checkpoints = storage_metrics(
        client.app.state.settings.database_url,
        case_ids,
    )
    assert len(set(case_ids)) == size
    assert {run.route for run in runs} == {EXPECTED_ROUTE}
    assert all(
        run.provider_calls == len(PROBE_DOCUMENTS) for run in runs
    )
    ordinary = [value for run in runs for value in run.ordinary_ms]
    return CohortRun(
        size=size,
        elapsed_seconds=elapsed,
        ordinary_p95_ms=percentile(ordinary, 95),
        review_ready_p95_ms=percentile(
            [run.review_ready_ms for run in runs], 95
        ),
        provider_p95_ms=percentile(provider_durations, 95),
        provider_max_active=max_active,
        provider_calls_per_case=max(run.provider_calls for run in runs),
        database_max_checked_out=max(pool_samples, default=0),
        database_pool_size=pool.size(),
        stored_bytes_per_case=stored,
        upload_bytes_per_case=uploads,
        checkpoint_bytes_per_case=checkpoints,
        queue_p95_ms=queue_p95(client, underwriter),
    )


# Print the decision measures without presenting them as capacity claims.
def report(cohorts: list[CohortRun], ocr_seconds: float) -> None:
    print("Pilot probe passed: fresh synthetic cases, fake provider")
    print(f"  OCR median: {ocr_seconds:.3f}s/page ({OCR_SAMPLES} pages)")
    for run in cohorts:
        print(f"  {run.size}-case cohort: {run.elapsed_seconds:.2f}s")
        print(
            f"    p95 ordinary {run.ordinary_p95_ms:.0f}ms; "
            f"review-ready {run.review_ready_p95_ms:.0f}ms; "
            f"queue {run.queue_p95_ms:.0f}ms"
        )
        print(
            f"    provider p95 {run.provider_p95_ms:.2f}ms; "
            f"max active {run.provider_max_active}; "
            f"calls/case {run.provider_calls_per_case}"
        )
        print(
            f"    database max checked out "
            f"{run.database_max_checked_out}/{run.database_pool_size}; "
            f"stored {run.stored_bytes_per_case:.0f}B/case"
        )
        print(
            f"    uploads {run.upload_bytes_per_case:.0f}B/case; "
            f"checkpoints {run.checkpoint_bytes_per_case:.0f}B/case"
        )
    print("  note: local synthetic measurements, not capacity claims")


# Run both bounded cohorts and enforce the plan's local acceptance limits.
def run_probe() -> None:
    from underwriteflow.cases import router as cases_router

    provider = MeasuredFakeProvider()
    cases_router.build_provider = lambda _settings: provider
    run_id = uuid4().hex
    ocr_seconds = measure_ocr_seconds_per_page()
    with TestClient(create_app()) as client:
        administrator = login(client, *ADMINISTRATOR)
        activation = client.post(
            "/api/v1/products/motor-private-car/activate",
            headers=administrator,
            json={"version": PRODUCT_VERSION},
        )
        assert activation.status_code == 200, activation.text
        applicant = login(client, *APPLICANT)
        underwriter = login(client, *UNDERWRITER)
        cohorts = [
            run_cohort(
                client,
                run_id,
                size,
                applicant,
                underwriter,
                administrator,
                provider,
            )
            for size in COHORT_SIZES
        ]
    report(cohorts, ocr_seconds)
    for cohort in cohorts:
        assert cohort.elapsed_seconds <= BUDGET_SECONDS
        assert cohort.ordinary_p95_ms <= 2_000
        assert cohort.review_ready_p95_ms <= 60_000
        assert cohort.provider_calls_per_case <= MAX_DOCUMENT_BRANCHES
        assert cohort.provider_max_active <= (
            MAX_WORKERS * MAX_DOCUMENT_BRANCHES
        )


if __name__ == "__main__":
    run_probe()
