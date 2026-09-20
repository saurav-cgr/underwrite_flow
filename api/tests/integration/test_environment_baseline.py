"""Integration coverage for the common baseline every environment starts with.

The baseline is exactly what `alembic upgrade head` plus the built-in product
import leave behind: schema, authorization catalogue, three fictional demo
identities, and every built-in product version. It contains no business
record. These tests build one throwaway database so the assertions describe
fresh storage rather than a developer's working stack.
"""

import os
import subprocess
from collections.abc import Iterator

import psycopg
import pytest

ADMIN_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/postgres"
)
BASELINE_DATABASE = "underwriteflow_baseline"
BASELINE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/" + BASELINE_DATABASE
)
BASELINE_ASYNC_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password@"
    "db:5433/" + BASELINE_DATABASE
)

DEMO_ACCOUNTS = {
    "applicant@synthetic.test": "Applicant",
    "underwriter@synthetic.test": "Underwriter",
    "administrator@synthetic.test": "Administrator",
}

BUSINESS_TABLES = (
    "cases",
    "submissions",
    "documents",
    "extracted_fields",
    "validations",
    "risk_signals",
    "recommendations",
    "reviews",
    "handoffs",
)

EXPECTED_PRODUCT_VERSIONS = 10


# Run one bootstrap command against the throwaway baseline database.
def _bootstrap(command: list[str]) -> None:
    environment = dict(os.environ, DATABASE_URL=BASELINE_ASYNC_URL)
    subprocess.run(command, cwd="/app", check=True, env=environment)


# Create the throwaway database, dropping any leftover from an earlier run.
def _recreate_database() -> None:
    with psycopg.connect(ADMIN_URL, autocommit=True) as connection:
        connection.execute(
            f'DROP DATABASE IF EXISTS "{BASELINE_DATABASE}" WITH (FORCE)'
        )
        connection.execute(f'CREATE DATABASE "{BASELINE_DATABASE}"')


# Initialize one fresh baseline database and drop it after the module runs.
@pytest.fixture(scope="module")
def baseline() -> Iterator[None]:
    _recreate_database()
    _bootstrap(["alembic", "upgrade", "head"])
    _bootstrap(["python", "-m", "underwriteflow.products.import_configs"])
    try:
        yield
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as connection:
            connection.execute(
                f'DROP DATABASE IF EXISTS "{BASELINE_DATABASE}" WITH (FORCE)'
            )


# Count rows in one baseline table.
def _count(table: str) -> int:
    with psycopg.connect(BASELINE_URL) as connection:
        row = connection.execute(f"SELECT count(*) FROM {table}").fetchone()
    return row[0]


# Given fresh storage, when initialized, then exactly three demo accounts
# exist and every one of them is active.
def test_baseline_has_the_three_active_demo_identities(baseline) -> None:
    with psycopg.connect(BASELINE_URL) as connection:
        rows = connection.execute(
            "SELECT email, role, is_active FROM users ORDER BY email"
        ).fetchall()

    assert {row[0]: row[1] for row in rows} == DEMO_ACCOUNTS
    assert all(row[2] for row in rows)


# Given fresh storage, when initialized, then the authorization catalogue
# carries the three role codes and their granted permissions.
def test_baseline_has_roles_permissions_and_mappings(baseline) -> None:
    with psycopg.connect(BASELINE_URL) as connection:
        roles = connection.execute(
            "SELECT code FROM roles ORDER BY code"
        ).fetchall()
        permission_count = connection.execute(
            "SELECT count(*) FROM permissions"
        ).fetchone()[0]
        grant_count = connection.execute(
            "SELECT count(*) FROM role_permissions"
        ).fetchone()[0]
        mapping_count = connection.execute(
            "SELECT count(*) FROM user_role_mappings"
        ).fetchone()[0]

    assert {row[0] for row in roles} == {
        "applicant",
        "underwriter",
        "administrator",
    }
    assert permission_count > 0
    assert grant_count > 0
    assert mapping_count == len(DEMO_ACCOUNTS)


# Given fresh storage, when initialized, then every built-in product
# configuration version is imported with its rulebook.
def test_baseline_imports_every_built_in_product_version(baseline) -> None:
    with psycopg.connect(BASELINE_URL) as connection:
        products = connection.execute(
            "SELECT code FROM products ORDER BY code"
        ).fetchall()

    assert {row[0] for row in products} == {
        "motor-private-car",
        "life-individual-term",
        "health-individual-family-floater",
    }
    assert _count("product_versions") == EXPECTED_PRODUCT_VERSIONS
    assert _count("rulebook_versions") == EXPECTED_PRODUCT_VERSIONS


# Given fresh storage, when initialized, then no business record exists.
@pytest.mark.parametrize("table", BUSINESS_TABLES)
def test_baseline_creates_no_business_record(baseline, table: str) -> None:
    assert _count(table) == 0


# Given an initialized baseline, when bootstrap runs again, then no row is
# duplicated and the demo identities stay unchanged.
def test_reinitialization_creates_no_duplicate(baseline) -> None:
    before = {
        table: _count(table)
        for table in ("users", "products", "product_versions",
                      "rulebook_versions", "roles", "permissions",
                      "role_permissions", "user_role_mappings")
    }

    _bootstrap(["alembic", "upgrade", "head"])
    _bootstrap(["python", "-m", "underwriteflow.products.import_configs"])

    after = {table: _count(table) for table in before}
    assert after == before
    for table in BUSINESS_TABLES:
        assert _count(table) == 0
