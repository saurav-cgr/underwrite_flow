from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from underwriteflow.app import create_app
from underwriteflow.config import Settings


DATABASE_URL = "postgresql://underwriteflow:synthetic-local-password@db:5433/underwriteflow"


# Verify an underwriter resumes a checkpoint and persists the governed review outcome.
def test_review_endpoint_resumes_checkpoint_and_records_decision() -> None:
    case_id = uuid4()
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE role = %s LIMIT 1", ("Applicant",))
            applicant_id = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT product_versions.id, rulebook_versions.id
                FROM product_versions
                JOIN products ON products.id = product_versions.product_id
                JOIN rulebook_versions
                  ON rulebook_versions.product_version_id = product_versions.id
                WHERE products.code = %s
                LIMIT 1
                """,
                ("motor-private-car",),
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO cases (
                    id, applicant_user_id, product_version_id, rulebook_version_id,
                    status, workflow_thread_id, idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    applicant_id,
                    product_version_id,
                    rulebook_version_id,
                    "new",
                    f"case-{case_id}",
                    f"review-{case_id}",
                ),
            )
            cursor.execute(
                """
                INSERT INTO submissions (id, case_id, payload)
                VALUES (%s, %s, %s)
                """,
                (uuid4(), case_id, '{"application": {"vehicle_age": 2}}'),
            )
            for code in ("identity_record", "vehicle_record"):
                cursor.execute(
                    """
                    INSERT INTO documents (
                        id, case_id, document_code, filename, content_type,
                        storage_key, content_hash, byte_size, page_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(),
                        case_id,
                        code,
                        f"{code}.pdf",
                        "application/pdf",
                        f"{case_id}/{code}.pdf",
                        f"synthetic-{code}",
                        32,
                        1,
                    ),
                )

    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant_login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "applicant@synthetic.test",
                    "password": "underwriteflow-demo-applicant",
                },
            )
            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit",
                headers={
                    "Authorization": f"Bearer {applicant_login.json()['token']}"
                },
            )
            assert submitted.status_code == 200, submitted.text
            login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "underwriter@synthetic.test",
                    "password": "underwriteflow-demo-underwriter",
                },
            )
            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            start = client.post(f"/api/v1/reviews/{case_id}/start", headers=headers)
            resumed_start = client.post(
                f"/api/v1/reviews/{case_id}/start",
                headers=headers,
            )
            admin_login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "administrator@synthetic.test",
                    "password": "underwriteflow-demo-administrator",
                },
            )
            admin_response = client.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm"},
                headers={"Authorization": f"Bearer {admin_login.json()['token']}"},
            )
            response = client.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm"},
                headers=headers,
            )
            restarted = client.post(f"/api/v1/reviews/{case_id}/start", headers=headers)

        assert login.status_code == 200
        assert start.status_code == 200, start.text
        pack = start.json()
        assert pack["recommendation"]["route"] == "expedited"
        assert pack["missing_information"] == []
        assert pack["specialist_options"]
        assert any(item["source_locator"] for item in pack["evidence"])
        assert resumed_start.status_code == 200
        assert resumed_start.json() == pack
        assert admin_login.status_code == 200
        assert admin_response.status_code == 403
        assert response.status_code == 200
        assert response.json()["selected_route"] == "expedited"
        assert response.json()["status"] == "confirmed"
        assert restarted.status_code == 409
    finally:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_events DISABLE TRIGGER audit_events_append_only")
                try:
                    cursor.execute(
                        "DELETE FROM extracted_fields WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM validations WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM risk_signals WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM documents WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute("DELETE FROM audit_events WHERE case_id = %s", (case_id,))
                    cursor.execute("DELETE FROM reviews WHERE case_id = %s", (case_id,))
                    cursor.execute("DELETE FROM recommendations WHERE case_id = %s", (case_id,))
                    cursor.execute("DELETE FROM submissions WHERE case_id = %s", (case_id,))
                    cursor.execute("DELETE FROM cases WHERE id = %s", (case_id,))
                finally:
                    cursor.execute("ALTER TABLE audit_events ENABLE TRIGGER audit_events_append_only")
