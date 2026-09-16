"""Shared helpers for the review, checkpoint, and audit integration tests.

The seeding helper writes the rows intake would create, so a test can start
from a case that is ready to submit without depending on product activation.
"""

import shutil
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    UPLOAD_ROOT,
    text_pdf,
    write_upload,
)

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, account: tuple[str, str]) -> dict[str, str]:
    email, password = account
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Write the rows and upload files a submittable synthetic motor case needs.
def seed_case(case_id: UUID) -> None:
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
                WHERE products.code = %s
                LIMIT 1
                """,
                ("motor-private-car",),
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO cases (
                    id, applicant_user_id, product_version_id,
                    rulebook_version_id, status, workflow_thread_id,
                    idempotency_key
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
    # The workflow extracts from the volume, so the referenced files must
    # exist and carry the configured field lines.
    for document_code, lines in (
        ("identity_record", IDENTITY_ONLY_LINES),
        ("vehicle_record", MOTOR_EVIDENCE_LINES),
    ):
        write_upload(case_id, document_code, text_pdf(lines))


# Read one case's recorded decisions, oldest review cycle first.
def read_decisions(case_id: UUID) -> list[tuple[int, str, str | None]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT review_cycle, action, selected_route FROM reviews "
                "WHERE case_id = %s ORDER BY review_cycle",
                (case_id,),
            )
            return [tuple(row) for row in cursor.fetchall()]


# Snapshot one case's audit rows so a later comparison proves immutability.
def read_audit(case_id: UUID) -> list[tuple[str, str, str]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, event_type, occurred_at FROM audit_events "
                "WHERE case_id = %s ORDER BY occurred_at, id",
                (case_id,),
            )
            return [
                (str(row[0]), row[1], row[2].isoformat())
                for row in cursor.fetchall()
            ]


# Count the queue handoffs recorded for one case.
def count_handoffs(case_id: UUID) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM handoffs WHERE case_id = %s",
                (case_id,),
            )
            return cursor.fetchone()[0]


# Remove one synthetic case and every row the workflow wrote for it.
def remove_case(case_id: UUID) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            for table in (
                "checkpoint_writes",
                "checkpoint_blobs",
                "checkpoints",
            ):
                cursor.execute(
                    f"DELETE FROM {table} WHERE thread_id LIKE %s",
                    (f"case-{case_id}%",),
                )
            cursor.execute(
                "DELETE FROM handoffs WHERE case_id = %s", (case_id,)
            )
            # Audit events are append-only, so the guard is lifted briefly.
            cursor.execute(
                "ALTER TABLE audit_events DISABLE TRIGGER "
                "audit_events_append_only"
            )
            try:
                for statement in (
                    "DELETE FROM audit_events WHERE case_id = %s",
                    "DELETE FROM extracted_fields WHERE case_id = %s",
                    "DELETE FROM validations WHERE case_id = %s",
                    "DELETE FROM risk_signals WHERE case_id = %s",
                    "DELETE FROM reviews WHERE case_id = %s",
                    "DELETE FROM recommendations WHERE case_id = %s",
                    "DELETE FROM documents WHERE case_id = %s",
                    "DELETE FROM submissions WHERE case_id = %s",
                    "DELETE FROM cases WHERE id = %s",
                ):
                    cursor.execute(statement, (case_id,))
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events ENABLE TRIGGER "
                    "audit_events_append_only"
                )
    shutil.rmtree(UPLOAD_ROOT / str(case_id), ignore_errors=True)
