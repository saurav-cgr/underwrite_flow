"""Shared identity and role database helpers for the test suites.

These helpers seed and inspect rows directly, so a test can start from a case
that is ready to submit without depending on product activation. Helpers that
drive the API live beside this module in `fixtures.support`; case, product-
status, and evidence helpers live in `fixtures.case_fixtures` to keep this
file under the project's 400-line limit.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID, uuid4

import psycopg

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


# Delete one synthetic user together with the audit rows it authored.
#
# Audit events are append-only and hold a foreign key to their actor, so a
# user that signed in cannot be removed until its own events are. The guard is
# lifted only for this deletion, mirroring `remove_case`.
def remove_user_with_audit(user_id: UUID) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE audit_events DISABLE TRIGGER "
                "audit_events_append_only"
            )
            try:
                cursor.execute(
                    "DELETE FROM audit_events WHERE actor_user_id = %s",
                    (user_id,),
                )
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events ENABLE TRIGGER "
                    "audit_events_append_only"
                )


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
        remove_user_with_audit(user_id)


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


# Delete one role created through the API, cascading its mappings.
def remove_role_by_code(code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM roles WHERE code = %s", (code,))


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


# Case, product-status, and evidence helpers moved to keep this file
# under the 400-line limit; re-exported here for existing imports.
from fixtures.case_fixtures import (  # noqa: E402
    SEED_APPLICATION_PAYLOAD,
    clear_recommendation_summary,
    count_handoffs,
    motor_status,
    product_version_audit,
    read_audit,
    read_decisions,
    remove_case,
    remove_upload,
    seed_case,
    set_motor_status,
)
