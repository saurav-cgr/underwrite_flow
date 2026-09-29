"""Database checks for the additive versioned knowledge schema."""

import psycopg
import pytest


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Verify the knowledge tables and the one-active uniqueness rule exist.
def test_knowledge_tables_and_active_index() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name IN (%s, %s, %s, %s) ORDER BY table_name",
                (
                    "case_guidance",
                    "knowledge_versions",
                    "knowledge_passages",
                    "case_knowledge_pins",
                ),
            )
            assert [row[0] for row in cursor.fetchall()] == [
                "case_guidance",
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


# Verify stored guidance has one immutable slot per case cycle and kind.
def test_case_guidance_unique_cycle_kind() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT constraint_name FROM "
                "information_schema.table_constraints "
                "WHERE table_name = %s AND constraint_name = %s",
                ("case_guidance", "uq_case_guidance_cycle_kind"),
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


# Verify the retrieval extension, generated search column, and indexes exist.
def test_retrieval_columns_and_indexes() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extname FROM pg_extension WHERE extname = %s",
                ("vector",),
            )
            assert cursor.fetchone() == ("vector",)
            cursor.execute(
                "SELECT format_type(a.atttypid, a.atttypmod) "
                "FROM pg_attribute AS a "
                "JOIN pg_class AS c ON c.oid = a.attrelid "
                "WHERE c.relname = %s AND a.attname = %s",
                ("knowledge_passages", "embedding"),
            )
            assert cursor.fetchone() == ("vector(768)",)
            cursor.execute(
                "SELECT is_generated, generation_expression "
                "FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                ("knowledge_passages", "search_vector"),
            )
            search_vector = cursor.fetchone()
            assert search_vector is not None
            assert search_vector[0] == "ALWAYS"
            assert "to_tsvector" in search_vector[1]
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = %s AND indexname IN (%s, %s) "
                "ORDER BY indexname",
                (
                    "knowledge_passages",
                    "ix_knowledge_passages_search_vector",
                    "ix_knowledge_passages_embedding_hnsw",
                ),
            )
            indexes = cursor.fetchall()
            assert [row[0] for row in indexes] == [
                "ix_knowledge_passages_embedding_hnsw",
                "ix_knowledge_passages_search_vector",
            ]
            assert "vector_cosine_ops" in indexes[0][1]
