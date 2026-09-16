"""Review-cycle scoping and single-decision guarantees for one case."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.synthetic_pdf import blank_pdf

from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

MOTOR_PAYLOAD = {
    "vehicle_age": 2,
    "vehicle_use": "personal",
    "prior_claims": 0,
}

DOCUMENT_CODES = ["identity_record", "vehicle_record"]


# Log in one fictional demo role and return bearer headers.
def login(
    client: TestClient, email: str, password: str
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Set the built-in synthetic motor product active or back to draft.
def set_motor_status(status: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE product_versions SET status = %s WHERE product_id "
                "= (SELECT id FROM products WHERE code = %s)",
                (status, "motor-private-car"),
            )
            cursor.execute(
                "UPDATE products SET status = %s WHERE code = %s",
                (status, "motor-private-car"),
            )


# Create, upload, and submit one case that recommends more information.
def prepare_review_case(
    client: TestClient, applicant: dict[str, str]
) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": MOTOR_PAYLOAD,
            "document_codes": DOCUMENT_CODES,
        },
        headers=applicant,
    )
    assert created.status_code == 200, created.text
    case_id = created.json()["id"]
    for code in DOCUMENT_CODES:
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "document": (
                    "synthetic.pdf",
                    blank_pdf(),
                    "application/pdf",
                )
            },
            data={"document_code": code},
            headers=applicant,
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = client.post(
        f"/api/v1/cases/{case_id}/submit", headers=applicant
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["recommendation"]["route"] == "needs_information"
    return case_id


# Read one case's persisted review rows in cycle order.
def read_reviews(case_id: str) -> list[tuple[int, str, str | None]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT review_cycle, action, selected_route FROM reviews "
                "WHERE case_id = %s ORDER BY review_cycle",
                (case_id,),
            )
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


# Count the persisted review-decision audit events for one case.
def count_review_events(case_id: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM audit_events WHERE case_id = %s "
                "AND event_type = %s",
                (case_id, "underwriter_reviewed"),
            )
            return cursor.fetchone()[0]


# Read one case's persisted status and review cycle.
def read_case_state(case_id: str) -> tuple[str, int]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, review_cycle FROM cases WHERE id = %s",
                (case_id,),
            )
            return cursor.fetchone()


# Verify the cycle after a resubmission accepts a new decision instead of
# replaying the previous cycle's persisted outcome.
def test_second_cycle_decision_resumes_the_new_checkpoint() -> None:
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            underwriter = login(
                client,
                "underwriter@synthetic.test",
                "underwriteflow-demo-underwriter",
            )
            case_id = prepare_review_case(client, applicant)
            first = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={
                    "action": "request_information",
                    "reason": "Synthetic extra evidence required",
                    "evidence_acknowledged": True,
                },
            )
            assert first.status_code == 200, first.text
            assert first.json()["status"] == "needs_information"
            resubmitted = client.post(
                f"/api/v1/cases/{case_id}/resubmit", headers=applicant
            )
            assert resubmitted.status_code == 200, resubmitted.text
            decision = {
                "action": "override",
                "selected_route": "standard",
                "reason": "Synthetic second-cycle route",
                "evidence_acknowledged": True,
            }
            second = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json=decision,
            )
            assert second.status_code == 200, second.text
            assert second.json()["status"] == "overridden"
            assert second.json()["selected_route"] == "standard"
            retry = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json=decision,
            )
            assert retry.status_code == 200, retry.text
            assert retry.json() == second.json()

        assert read_reviews(case_id) == [
            (0, "request_information", None),
            (1, "override", "standard"),
        ]
        assert count_review_events(case_id) == 2
        assert read_case_state(case_id) == ("overridden", 1)
    finally:
        set_motor_status("draft")


# Verify two simultaneous decisions for one case settle on a single matching
# review, checkpoint outcome, and audit event.
def test_concurrent_decisions_settle_on_one_outcome() -> None:
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            underwriter = login(
                client,
                "underwriter@synthetic.test",
                "underwriteflow-demo-underwriter",
            )
            case_id = prepare_review_case(client, applicant)
            commands = [
                {
                    "action": "override",
                    "selected_route": "standard",
                    "reason": "Synthetic first route",
                    "evidence_acknowledged": True,
                },
                {
                    "action": "override",
                    "selected_route": "expedited",
                    "reason": "Synthetic second route",
                    "evidence_acknowledged": True,
                },
            ]
            # Release both requests together so the race is genuine.
            barrier = Barrier(len(commands))

            def decide(command: dict[str, object]):
                barrier.wait(timeout=30)
                return client.post(
                    f"/api/v1/reviews/{case_id}",
                    headers=underwriter,
                    json=command,
                )

            with ThreadPoolExecutor(max_workers=len(commands)) as pool:
                responses = list(pool.map(decide, commands))

        statuses = [response.status_code for response in responses]
        assert statuses == [200, 200], [
            response.text for response in responses
        ]
        assert responses[0].json() == responses[1].json()
        settled = responses[0].json()
        assert settled["status"] == "overridden"
        assert read_reviews(case_id) == [
            (0, "override", settled["selected_route"])
        ]
        assert count_review_events(case_id) == 1
        assert read_case_state(case_id) == ("overridden", 0)
    finally:
        set_motor_status("draft")
