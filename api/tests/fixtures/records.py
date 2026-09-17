"""Shared database and upload-volume helpers for the test suites.

These helpers seed and inspect rows directly, so a test can start from a case
that is ready to submit without depending on product activation. Helpers that
drive the API live beside this module in `fixtures.support`.
"""

import shutil
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID, uuid4

import psycopg

from fixtures.synthetic_pdf import (
    DEFAULT_DOCUMENT_CODES,
    MOTOR_DOCUMENT_LINES,
    UPLOAD_ROOT,
    text_pdf,
    write_upload,
)

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

# Legacy `users.role` values mapped to the stable lowercase role codes that
# dynamic roles replace them with, one mapping per known role.
ROLE_CODES: dict[str, str] = {
    "Applicant": "applicant",
    "Underwriter": "underwriter",
    "Administrator": "administrator",
}

# Placeholder Argon2-shaped hash for synthetic users that never log in.
SYNTHETIC_PASSWORD_HASH = "synthetic-demonstration-hash"


# Insert one fictional synthetic user and return its generated identifier.
def create_user(
    role: str = "Applicant",
    email: str | None = None,
    display_name: str = "Synthetic Test User",
    is_active: bool = True,
) -> UUID:
    user_id = uuid4()
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (id, email, display_name, role, "
                "password_hash, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    user_id,
                    email or f"synthetic-{user_id}@example.test",
                    display_name,
                    role,
                    SYNTHETIC_PASSWORD_HASH,
                    is_active,
                ),
            )
    return user_id


# Delete one synthetic user, which requires every row it owns to be gone
# first, because `cases.applicant_user_id` and the seeded demo accounts must
# stay exactly as the migration left them.
def remove_user(user_id: UUID) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))


# Create a synthetic user for one test and always delete it afterwards.
@contextmanager
def synthetic_user(
    role: str = "Applicant",
    email: str | None = None,
    display_name: str = "Synthetic Test User",
    is_active: bool = True,
) -> Iterator[UUID]:
    user_id = create_user(
        role=role,
        email=email,
        display_name=display_name,
        is_active=is_active,
    )
    try:
        yield user_id
    finally:
        remove_user(user_id)


# Attach one seeded role to a synthetic user, replacing any existing mapping.
def assign_role(user_id: UUID, role_code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_role_mappings (user_id, role_id) "
                "SELECT %s, roles.id FROM roles WHERE roles.code = %s "
                "ON CONFLICT (user_id) DO UPDATE SET role_id = "
                "EXCLUDED.role_id",
                (user_id, role_code),
            )


# Read the permission scopes one configured role currently grants.
def role_scopes(role_code: str) -> tuple[str, ...]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT permissions.code FROM role_permissions "
                "JOIN permissions ON permissions.id = "
                "role_permissions.permission_id "
                "JOIN roles ON roles.id = role_permissions.role_id "
                "WHERE roles.code = %s ORDER BY permissions.code",
                (role_code,),
            )
            return tuple(row[0] for row in cursor.fetchall())


# Create one synthetic non-system role for a test and always delete it.
@contextmanager
def synthetic_role(
    code: str, scopes: Sequence[str], is_active: bool = True
) -> Iterator[str]:
    role_id = uuid4()
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO roles (id, code, title, is_active, is_system) "
                "VALUES (%s, %s, %s, %s, false)",
                (role_id, code, f"Synthetic {code}", is_active),
            )
            for scope in scopes:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "SELECT %s, permissions.id FROM permissions "
                    "WHERE permissions.code = %s",
                    (role_id, scope),
                )
    try:
        yield code
    finally:
        # Deleting the role cascades its mappings and permission pairs.
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM roles WHERE id = %s", (role_id,))


# Read the current status of the built-in synthetic motor product.
def motor_status() -> str:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM products WHERE code = %s",
                ("motor-private-car",),
            )
            row = cursor.fetchone()
    return row[0] if row else "draft"


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


# Replace one case's persisted recommendation summary with an empty object.
def clear_recommendation_summary(case_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE recommendations SET summary = '{}'::jsonb "
                "WHERE case_id = %s",
                (case_id,),
            )


# Delete one uploaded file so its extraction branch fails on the volume.
def remove_upload(case_id: str, document_code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT storage_key FROM documents WHERE case_id = %s "
                "AND document_code = %s",
                (case_id, document_code),
            )
            row = cursor.fetchone()
    assert row is not None
    (UPLOAD_ROOT / row[0]).unlink()


# Write the rows and upload files a submittable synthetic motor case needs.
def seed_case(
    case_id: UUID, document_codes: Sequence[str] = DEFAULT_DOCUMENT_CODES
) -> None:
    uploads = {
        code: text_pdf(MOTOR_DOCUMENT_LINES[code]) for code in document_codes
    }
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
            for code, content in uploads.items():
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
                        len(content),
                        1,
                    ),
                )
    # The workflow extracts from the volume, so the referenced files must
    # exist and carry the configured field lines.
    for code, content in uploads.items():
        write_upload(case_id, code, content)


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
