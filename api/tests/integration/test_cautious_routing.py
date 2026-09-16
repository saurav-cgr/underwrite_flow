"""Routing that must err toward a human instead of a confident route."""

import json
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from synthetic_pdf import (
    MOTOR_EVIDENCE_LINES,
    UPLOAD_ROOT,
    blank_pdf,
    text_pdf,
)

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


# Read the stored configuration text of the active motor version.
def read_motor_configuration() -> str:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT configuration::text FROM product_versions "
                "WHERE product_id = (SELECT id FROM products WHERE code = %s) "
                "ORDER BY version LIMIT 1",
                ("motor-private-car",),
            )
            return cursor.fetchone()[0]


# Replace the stored configuration text of the active motor version.
def write_motor_configuration(text: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE product_versions SET configuration = %s::jsonb "
                "WHERE product_id = (SELECT id FROM products WHERE code = %s)",
                (text, "motor-private-car"),
            )


# Break one configured rule so the stored version no longer validates.
def break_motor_configuration() -> str:
    original = read_motor_configuration()
    payload = json.loads(original)
    payload["specialist_labels"] = []
    write_motor_configuration(json.dumps(payload))
    return original


# Create one motor case and upload the documents it requires.
def prepare_case(client: TestClient, applicant: dict[str, str]) -> str:
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
    uploads = [
        ("identity_record", blank_pdf()),
        ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ]
    for code, content in uploads:
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "document": (
                    "synthetic.pdf",
                    content,
                    "application/pdf",
                )
            },
            data={"document_code": code},
            headers=applicant,
        )
        assert uploaded.status_code == 200, uploaded.text
    return case_id


# Delete one uploaded file so its local extraction fails on the volume.
def remove_upload(case_id: str, document_code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT storage_key FROM documents WHERE case_id = %s "
                "AND document_code = %s",
                (case_id, document_code),
            )
            storage_key = cursor.fetchone()[0]
    (UPLOAD_ROOT / storage_key).unlink()


# Read one case's persisted status and recommended route.
def read_case(case_id: str) -> tuple[str, str | None]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT cases.status, recommendations.route FROM cases "
                "LEFT JOIN recommendations "
                "ON recommendations.case_id = cases.id WHERE cases.id = %s",
                (case_id,),
            )
            return cursor.fetchone()


# Verify an unreadable pinned configuration reaches a human instead of failing.
def test_unreadable_pinned_configuration_routes_to_manual_review() -> None:
    set_motor_status("active")
    original = None
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            case_id = prepare_case(client, applicant)

            # Corrupt the pinned version after intake, so the case now pins a
            # configuration the application can no longer read.
            original = break_motor_configuration()

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"
            assert submitted.json()["recommendation"]["route"] == "manual"

            underwriter = login(
                client,
                "underwriter@synthetic.test",
                "underwriteflow-demo-underwriter",
            )
            opened = client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            )
            assert opened.status_code == 200, opened.text
            pack = opened.json()
            assert pack["recommendation"]["route"] == "manual"
            assert pack["specialist_options"] == []
            assert pack["missing_information"] == []
            assert pack["extraction_failures"] == [
                {
                    "rule_code": "unsupported_product",
                    "details": {
                        "rule_code": "unsupported_product",
                        "status": "error",
                        "details": {
                            "reason": "unreadable_product_configuration"
                        },
                    },
                }
            ]

            decided = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={
                    "action": "confirm",
                    "specialist_label": "manual review desk",
                    "evidence_acknowledged": True,
                },
            )
            assert decided.status_code == 200, decided.text
            assert decided.json()["status"] == "overridden"
            assert decided.json()["selected_route"] == "specialist"

        assert read_case(case_id) == ("overridden", "manual")
    finally:
        if original is not None:
            write_motor_configuration(original)
        set_motor_status("draft")


# Verify a failed document branch routes to specialist review even when a
# sibling document supplies every requested field.
def test_failed_branch_routes_to_specialist_review() -> None:
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
            case_id = prepare_case(client, applicant)

            # Only the identity branch fails, and the vehicle record still
            # supplies vehicle_age, vehicle_use, and prior_claims.
            remove_upload(case_id, "identity_record")

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            recommendation = submitted.json()["recommendation"]
            assert recommendation["route"] == "specialist"
            assert recommendation["factors"] == ["processing_failure"]

        assert read_case(case_id) == ("underwriter_review", "specialist")
    finally:
        set_motor_status("draft")


# Verify intake against an unreadable active configuration is refused cleanly.
def test_unreadable_active_configuration_refuses_intake() -> None:
    set_motor_status("active")
    original = None
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            original = break_motor_configuration()

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

            assert created.status_code == 422, created.text
    finally:
        if original is not None:
            write_motor_configuration(original)
        set_motor_status("draft")


# Verify an upload against an unreadable pinned configuration is refused
# before anything reaches the upload volume.
def test_unreadable_pinned_configuration_refuses_upload() -> None:
    set_motor_status("active")
    original = None
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
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

            original = break_motor_configuration()

            uploaded = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={
                    "document": (
                        "synthetic.pdf",
                        text_pdf(MOTOR_EVIDENCE_LINES),
                        "application/pdf",
                    )
                },
                data={"document_code": "vehicle_record"},
                headers=applicant,
            )

            assert uploaded.status_code == 422, uploaded.text

        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM documents WHERE case_id = %s",
                    (case_id,),
                )
                assert cursor.fetchone()[0] == 0
    finally:
        if original is not None:
            write_motor_configuration(original)
        set_motor_status("draft")
