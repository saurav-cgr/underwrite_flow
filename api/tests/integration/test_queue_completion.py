from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from underwriteflow.app import create_app
from underwriteflow.config import Settings


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Verify completion is idempotent, queued, and present in immutable audit.
def test_confirmed_case_completes_once_and_is_auditable() -> None:
    case_id = uuid4()
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE role = %s LIMIT 1",
                ("Applicant",),
            )
            applicant_id = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT product_versions.id, rulebook_versions.id
                FROM product_versions
                JOIN products ON products.id = product_versions.product_id
                JOIN rulebook_versions
                  ON rulebook_versions.product_version_id = product_versions.id
                WHERE products.code = %s AND product_versions.version = %s
                """,
                ("motor-private-car", "v1"),
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO cases (
                    id, applicant_user_id, product_version_id,
                    rulebook_version_id,
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
                    f"queue-{case_id}",
                ),
            )
            cursor.execute(
                "INSERT INTO submissions (id, case_id, payload) "
                "VALUES (%s, %s, %s)",
                (
                    uuid4(),
                    case_id,
                    '{"application": {"vehicle_age": 2, '
                    '"vehicle_use": "personal", "prior_claims": 0}}',
                ),
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
            started = client.post(
                f"/api/v1/reviews/{case_id}/start",
                headers=headers,
            )
            assert started.status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "specialist",
                    "specialist_label": "motor inspection",
                    "reason": "Synthetic demonstration override",
                    "evidence_acknowledged": True,
                },
                headers=headers,
            ).status_code == 200
            pending_handoff = client.get(
                "/api/v1/queues",
                params={"awaiting_handoff": "true"},
                headers=headers,
            )
            completed = client.post(
                f"/api/v1/completion/{case_id}",
                headers=headers,
            )
            repeated = client.post(
                f"/api/v1/completion/{case_id}",
                headers=headers,
            )
            handoff_queue = client.get(
                "/api/v1/queues",
                params={"awaiting_handoff": "true"},
                headers=headers,
            )
            queue = client.get(
                "/api/v1/queues",
                params={
                    "status": "completed",
                    "product_code": "motor-private-car",
                    "specialist": "false",
                },
                headers=headers,
            )
            admin_login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "administrator@synthetic.test",
                    "password": "underwriteflow-demo-administrator",
                },
            )
            audit = client.get(
                f"/api/v1/audit/cases/{case_id}",
                headers={
                    "Authorization": (
                        f"Bearer {admin_login.json()['token']}"
                    )
                },
            )

        assert completed.status_code == 200
        assert repeated.status_code == 200
        assert repeated.json()["handoff_id"] == completed.json()["handoff_id"]
        assert completed.json()["route"] == "specialist"
        assert completed.json()["specialist_label"] == "motor inspection"
        assert pending_handoff.status_code == 200
        pending = [
            item
            for item in pending_handoff.json()
            if item["case_id"] == str(case_id)
        ]
        assert pending[0]["selected_route"] == "specialist"
        assert pending[0]["specialist_label"] == "motor inspection"
        assert pending[0]["awaiting_handoff"] is True
        assert all(
            item["case_id"] != str(case_id) for item in handoff_queue.json()
        )
        assert queue.status_code == 200
        assert queue.json()[0]["status"] == "completed"
        assert queue.json()[0]["selected_route"] == "specialist"
        assert queue.json()[0]["specialist_label"] == "motor inspection"
        assert audit.status_code == 200
        events = {event["event_type"]: event for event in audit.json()}
        event_types = set(events)
        assert "case_submitted" in event_types
        assert "underwriter_reviewed" in event_types
        assert "case_completed" in event_types
        reviewed_details = events["underwriter_reviewed"]["details"]
        assert reviewed_details["reason"] == (
            "Synthetic demonstration override"
        )
        assert events["underwriter_reviewed"]["actor_user_id"] is not None

        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM handoffs WHERE case_id = %s",
                    (case_id,),
                )
                cursor.execute(
                    "UPDATE reviews SET selected_route = %s WHERE case_id = %s",
                    ("manual", case_id),
                )
                cursor.execute(
                    "UPDATE cases SET status = %s WHERE id = %s",
                    ("confirmed", case_id),
                )
        with TestClient(create_app()) as client:
            rejected = client.post(
                f"/api/v1/completion/{case_id}",
                headers=headers,
            )

        assert rejected.status_code == 409
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM cases WHERE id = %s",
                    (case_id,),
                )
                assert cursor.fetchone()[0] == "confirmed"
                cursor.execute(
                    "SELECT COUNT(*) FROM handoffs WHERE case_id = %s",
                    (case_id,),
                )
                assert cursor.fetchone()[0] == 0
    finally:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (f"case-{case_id}:cycle-0",),
                )
                cursor.execute(
                    "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                    (f"case-{case_id}:cycle-0",),
                )
                cursor.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (f"case-{case_id}:cycle-0",),
                )
                cursor.execute(
                    "DELETE FROM handoffs WHERE case_id = %s",
                    (case_id,),
                )
                cursor.execute(
                    "ALTER TABLE audit_events DISABLE TRIGGER "
                    "audit_events_append_only"
                )
                try:
                    cursor.execute(
                        "DELETE FROM audit_events WHERE case_id = %s",
                        (case_id,),
                    )
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
                        "DELETE FROM reviews WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM recommendations WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM documents WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM submissions WHERE case_id = %s",
                        (case_id,),
                    )
                    cursor.execute(
                        "DELETE FROM cases WHERE id = %s",
                        (case_id,),
                    )
                finally:
                    cursor.execute(
                        "ALTER TABLE audit_events ENABLE TRIGGER "
                        "audit_events_append_only"
                    )
