"""Database checks for the additive versioned knowledge schema."""

import psycopg
import pytest


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Verify the three US2 tables and the one-active uniqueness rule exist.
def test_knowledge_tables_and_active_index() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name IN (%s, %s, %s) ORDER BY table_name",
                (
                    "knowledge_versions",
                    "knowledge_passages",
                    "case_knowledge_pins",
                ),
            )
            assert [row[0] for row in cursor.fetchall()] == [
                "case_knowledge_pins",
                "knowledge_passages",
                "knowledge_versions",
            ]
            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE indexname = %s",
                ("uq_knowledge_versions_one_active",),
            )
            assert cursor.fetchone() is not None


# Verify PostgreSQL rejects two active rows for one null-product scope.
def test_one_active_knowledge_version_per_scope() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with pytest.raises(psycopg.errors.UniqueViolation):
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO knowledge_versions "
                        "(id, scope, version, content_type, status, "
                        "content_hash, source, validation) VALUES "
                        "(gen_random_uuid(), 'regulation', 'test-a', "
                        "'public_regulation', 'active', 'a', '{}', '{}')"
                    )
                    cursor.execute(
                        "INSERT INTO knowledge_versions "
                        "(id, scope, version, content_type, status, "
                        "content_hash, source, validation) VALUES "
                        "(gen_random_uuid(), 'regulation', 'test-b', "
                        "'public_regulation', 'active', 'b', '{}', '{}')"
                    )
