"""Guards for the additive case-journey migration.

This suite drives alembic against the live test database directly, so it
fails until revision 08 adds a non-null ``cases.journey_type`` column that
defaults and backfills to ``new_business``, enforces a two-value check
constraint, and whose downgrade removes only what this revision introduces.
"""

import subprocess
from uuid import uuid4

import psycopg
import pytest

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Run one alembic subcommand against the live migration chain.
def run_alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], cwd="/app", check=True)


# Read the live column names for one table.
def table_columns(table: str) -> set[str]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            )
            return {row[0] for row in cursor.fetchall()}


# Read the stored journey_type for one case row.
def journey_type_of(case_id) -> str:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT journey_type FROM cases WHERE id = %s", (case_id,)
            )
            return cursor.fetchone()[0]


# Fetch one demo applicant and one imported product/rulebook version pair.
def fetch_reference_ids() -> tuple:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                ("applicant@synthetic.test",),
            )
            applicant_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT product_versions.id, rulebook_versions.id "
                "FROM product_versions "
                "JOIN rulebook_versions "
                "ON rulebook_versions.product_version_id = "
                "product_versions.id LIMIT 1"
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            return applicant_id, product_version_id, rulebook_version_id


CASE_COLUMNS = (
    "id, applicant_user_id, product_version_id, rulebook_version_id, status"
)


# Insert one minimal case row, omitting journey_type to exercise its default.
def insert_case(case_id, applicant_id, product_version_id, rulebook_id) -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO cases ({CASE_COLUMNS}) "
                "VALUES (%s, %s, %s, %s, %s)",
                (case_id, applicant_id, product_version_id, rulebook_id, "new"),
            )


# Insert one case row with an explicit journey_type value or NULL.
def insert_case_with_journey(
    case_id, applicant_id, product_version_id, rulebook_id, journey
) -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO cases ({CASE_COLUMNS}, journey_type) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    case_id,
                    applicant_id,
                    product_version_id,
                    rulebook_id,
                    "new",
                    journey,
                ),
            )


# Given a case row created before revision 08, when it upgrades and
# downgrades, then journey_type backfills, enforces its constraint, and the
# downgrade removes only the column this revision adds.
def test_revision_08_upgrade_backfill_constraint_and_downgrade() -> None:
    run_alembic("downgrade", "07")
    assert "journey_type" not in table_columns("cases")

    applicant_id, product_version_id, rulebook_version_id = (
        fetch_reference_ids()
    )
    legacy_case_id = uuid4()
    insert_case(
        legacy_case_id, applicant_id, product_version_id, rulebook_version_id
    )

    try:
        run_alembic("upgrade", "head")
        assert "journey_type" in table_columns("cases")
        assert journey_type_of(legacy_case_id) == "new_business"

        default_case_id = uuid4()
        insert_case(
            default_case_id,
            applicant_id,
            product_version_id,
            rulebook_version_id,
        )
        assert journey_type_of(default_case_id) == "new_business"

        renewal_case_id = uuid4()
        insert_case_with_journey(
            renewal_case_id,
            applicant_id,
            product_version_id,
            rulebook_version_id,
            "renewal",
        )
        assert journey_type_of(renewal_case_id) == "renewal"

        with pytest.raises(psycopg.errors.CheckViolation):
            insert_case_with_journey(
                uuid4(),
                applicant_id,
                product_version_id,
                rulebook_version_id,
                "reinstatement",
            )

        with pytest.raises(psycopg.errors.NotNullViolation):
            insert_case_with_journey(
                uuid4(),
                applicant_id,
                product_version_id,
                rulebook_version_id,
                None,
            )
    finally:
        run_alembic("downgrade", "07")
        assert "journey_type" not in table_columns("cases")
        run_alembic("upgrade", "head")
