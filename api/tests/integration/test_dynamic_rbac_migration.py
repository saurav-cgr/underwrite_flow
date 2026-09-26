"""Guards for the additive dynamic-RBAC migration and its constraints.

Every test here reads the live migrated schema, so the suite fails until
revision 07 creates the roles, permissions, role-permission, user-role, and
refresh-session tables, seeds the scope catalogue, and backfills exactly one
role mapping for each known legacy `users.role` value.
"""

from uuid import uuid4

import psycopg
import pytest

from underwriteflow.auth.schemas import UserRole

from fixtures.records import ROLE_CODES

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

RBAC_TABLES = (
    "roles",
    "permissions",
    "role_permissions",
    "user_role_mappings",
    "refresh_sessions",
)

TABLE_COLUMNS = {
    "roles": {
        "id",
        "code",
        "title",
        "description",
        "is_active",
        "is_system",
        "created_by_user_id",
        "created_at",
    },
    "permissions": {"id", "code", "title", "description", "created_at"},
    "role_permissions": {
        "role_id",
        "permission_id",
        "assigned_by_user_id",
        "created_at",
    },
    "user_role_mappings": {
        "user_id",
        "role_id",
        "assigned_by_user_id",
        "created_at",
    },
    "refresh_sessions": {
        "id",
        "user_id",
        "token_digest",
        "expires_at",
        "revoked_at",
        "replaced_by_id",
        "created_at",
    },
}

REQUIRED_SCOPES = (
    "cases:read",
    "cases:write",
    "cases:override",
    "users:manage",
    "schemas:edit",
    "audit:read",
)


# Run one read-only query and return every fetched row.
def fetch_all(statement: str, params: tuple = ()) -> list[tuple]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            return cursor.fetchall()


# Read the column names the live database records for one table.
def table_columns(table: str) -> set[str]:
    rows = fetch_all(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {row[0] for row in rows}


# Verify the migration adds every RBAC and refresh-session table.
def test_rbac_and_refresh_session_tables_exist() -> None:
    found = {
        row[0]
        for row in fetch_all(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
    }
    missing = sorted(set(RBAC_TABLES) - found)

    assert not missing, f"missing tables after revision 07: {missing}"


# Verify each new table exposes the columns the data model requires.
@pytest.mark.parametrize("table", sorted(TABLE_COLUMNS))
def test_rbac_table_declares_expected_columns(table: str) -> None:
    missing = sorted(TABLE_COLUMNS[table] - table_columns(table))

    assert not missing, f"{table} is missing columns: {missing}"


# Verify the legacy role column survives so the cutover stays reversible.
def test_legacy_user_role_column_is_preserved() -> None:
    rows = fetch_all(
        "SELECT email, role FROM users WHERE email LIKE %s ORDER BY email",
        ("%synthetic.test",),
    )

    assert [row[1] for row in rows] == [
        "Administrator",
        "Applicant",
        "Underwriter",
    ]


# Verify the seeded catalogue carries every scope this feature enforces.
def test_seeded_scope_catalogue_covers_required_scopes() -> None:
    codes = {row[0] for row in fetch_all("SELECT code FROM permissions")}
    missing = sorted(set(REQUIRED_SCOPES) - codes)

    assert not missing, f"permission catalogue is missing: {missing}"


# Verify one seeded system role exists for each stable role code.
def test_seeded_system_roles_cover_every_role_code() -> None:
    codes = {
        row[0]
        for row in fetch_all(
            "SELECT code FROM roles WHERE is_system IS TRUE"
        )
    }

    assert codes == set(ROLE_CODES.values())


# Verify every supported legacy role can map to exactly one stable code.
def test_role_codes_cover_every_supported_legacy_role() -> None:
    assert {role.value for role in UserRole} <= set(ROLE_CODES)
    assert len(set(ROLE_CODES.values())) == len(ROLE_CODES)


# Verify the backfill gives every existing user exactly one role mapping.
def test_every_user_backfills_exactly_one_role_mapping() -> None:
    rows = fetch_all(
        """
        SELECT users.email, users.role, roles.code,
               count(mappings.user_id) OVER (PARTITION BY users.id) AS mapped
        FROM users
        LEFT JOIN user_role_mappings AS mappings
          ON mappings.user_id = users.id
        LEFT JOIN roles ON roles.id = mappings.role_id
        ORDER BY users.email
        """
    )

    assert rows, "expected the migrated demo accounts to exist"
    for email, legacy_role, code, mapped in rows:
        assert mapped == 1, f"{email} has {mapped} role mappings"
        assert code == ROLE_CODES[legacy_role], (
            f"{email} mapped to {code!r}, expected "
            f"{ROLE_CODES[legacy_role]!r}"
        )


# Verify role codes are unique across configured roles.
def test_role_codes_are_unique() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SAVEPOINT duplicate_role")
            with pytest.raises(psycopg.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO roles (id, code, title, is_active, "
                    "is_system) VALUES (%s, %s, %s, true, false)",
                    (uuid4(), "underwriter", "Duplicate Underwriter"),
                )
            cursor.execute("ROLLBACK TO SAVEPOINT duplicate_role")


# Verify permission codes are unique across the fixed scope catalogue.
def test_permission_codes_are_unique() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SAVEPOINT duplicate_scope")
            with pytest.raises(psycopg.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO permissions (id, code, title) "
                    "VALUES (%s, %s, %s)",
                    (uuid4(), "cases:read", "Duplicate Case Read"),
                )
            cursor.execute("ROLLBACK TO SAVEPOINT duplicate_scope")


# Verify one role cannot claim the same permission scope twice.
def test_role_permission_pairs_are_unique() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT role_permissions.role_id, "
                "role_permissions.permission_id FROM role_permissions "
                "LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None, "expected at least one seeded mapping"
            cursor.execute("SAVEPOINT duplicate_pair")
            with pytest.raises(psycopg.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (%s, %s)",
                    row,
                )
            cursor.execute("ROLLBACK TO SAVEPOINT duplicate_pair")


# Verify a user can hold only one active role in this MVP.
def test_one_role_mapping_per_user_is_enforced() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT mappings.user_id, roles.id FROM user_role_mappings "
                "AS mappings JOIN roles ON roles.code = "
                "(SELECT code FROM roles WHERE code = 'applicant') LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None, "expected a backfilled applicant mapping"
            cursor.execute("SAVEPOINT duplicate_mapping")
            with pytest.raises(psycopg.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO user_role_mappings (user_id, role_id) "
                    "VALUES (%s, %s)",
                    row,
                )
            cursor.execute("ROLLBACK TO SAVEPOINT duplicate_mapping")


# Verify refresh digests are unique so one credential maps to one session.
def test_refresh_session_digests_are_unique() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users LIMIT 1")
            user_id = cursor.fetchone()[0]
            digest = f"synthetic-digest-{uuid4()}"
            insert = (
                "INSERT INTO refresh_sessions (id, user_id, token_digest, "
                "expires_at) VALUES (%s, %s, %s, now() + interval '1 hour')"
            )
            cursor.execute("SAVEPOINT first_digest")
            cursor.execute(insert, (uuid4(), user_id, digest))
            cursor.execute("SAVEPOINT reused_digest")
            with pytest.raises(psycopg.errors.UniqueViolation):
                cursor.execute(insert, (uuid4(), user_id, digest))
            cursor.execute("ROLLBACK TO SAVEPOINT reused_digest")
            cursor.execute("ROLLBACK TO SAVEPOINT first_digest")


# Verify a refresh session cannot be stored without an expiry.
def test_refresh_session_expiry_is_required() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users LIMIT 1")
            user_id = cursor.fetchone()[0]
            cursor.execute("SAVEPOINT missing_expiry")
            with pytest.raises(psycopg.errors.NotNullViolation):
                cursor.execute(
                    "INSERT INTO refresh_sessions (id, user_id, "
                    "token_digest, expires_at) VALUES (%s, %s, %s, NULL)",
                    (uuid4(), user_id, f"synthetic-{uuid4()}"),
                )
            cursor.execute("ROLLBACK TO SAVEPOINT missing_expiry")
