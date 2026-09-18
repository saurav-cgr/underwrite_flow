from uuid import UUID

import psycopg
import pytest

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Prove version pins persist and audit rows reject mutation.
def test_version_pins_and_audit_events_are_immutable() -> None:
    connection = psycopg.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    cursor.execute(
        "INSERT INTO users "
        "(id, email, display_name, role, password_hash, is_active) VALUES "
        "('00000000-0000-0000-0000-000000000001', "
        "'synthetic@example.test', 'Synthetic User', 'Applicant', "
        "'hash', true)"
    )
    cursor.execute(
        "INSERT INTO products (id, code, title, family, status) VALUES "
        "('00000000-0000-0000-0000-000000000002', 'synthetic', "
        "'Synthetic', 'motor', 'active')"
    )
    cursor.execute(
        "INSERT INTO product_versions "
        "(id, product_id, version, configuration, content_hash, status) "
        "VALUES ('00000000-0000-0000-0000-000000000003', "
        "'00000000-0000-0000-0000-000000000002', 'v1', '{}', "
        "'hash', 'active')"
    )
    cursor.execute(
        "INSERT INTO rulebook_versions "
        "(id, product_version_id, version, rules, content_hash) VALUES "
        "('00000000-0000-0000-0000-000000000004', "
        "'00000000-0000-0000-0000-000000000003', 'v1', '{}', 'hash')"
    )
    cursor.execute(
        "INSERT INTO cases "
        "(id, applicant_user_id, product_version_id, "
        "rulebook_version_id, status) VALUES "
        "('00000000-0000-0000-0000-000000000005', "
        "'00000000-0000-0000-0000-000000000001', "
        "'00000000-0000-0000-0000-000000000003', "
        "'00000000-0000-0000-0000-000000000004', 'new')"
    )
    cursor.execute(
        "SELECT product_version_id FROM cases WHERE id = "
        "'00000000-0000-0000-0000-000000000005'"
    )
    assert cursor.fetchone()[0] == UUID("00000000-0000-0000-0000-000000000003")
    cursor.execute(
        "INSERT INTO audit_events (id, event_type, details) VALUES "
        "('00000000-0000-0000-0000-000000000006', 'created', '{}')"
    )
    cursor.execute("SAVEPOINT audit_mutation")
    with pytest.raises(psycopg.errors.RaiseException):
        cursor.execute("UPDATE audit_events SET event_type = 'changed'")
    cursor.execute("ROLLBACK TO SAVEPOINT audit_mutation")
    connection.rollback()
    connection.close()


# Prove an append-only audit row also survives a deletion attempt.
def test_audit_event_rows_reject_deletion() -> None:
    connection = psycopg.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    cursor.execute(
        "INSERT INTO audit_events (id, event_type, details) VALUES "
        "('00000000-0000-0000-0000-000000000007', 'synthetic', '{}')"
    )
    cursor.execute("SAVEPOINT audit_removal")
    with pytest.raises(psycopg.errors.RaiseException):
        cursor.execute(
            "DELETE FROM audit_events WHERE id = "
            "'00000000-0000-0000-0000-000000000007'"
        )
    cursor.execute("ROLLBACK TO SAVEPOINT audit_removal")
    cursor.execute(
        "SELECT count(*) FROM audit_events WHERE id = "
        "'00000000-0000-0000-0000-000000000007'"
    )
    assert cursor.fetchone()[0] == 1
    connection.rollback()
    connection.close()


# Prove idempotency keys are scoped to one applicant, not globally unique.
def test_case_idempotency_keys_are_applicant_scoped() -> None:
    connection = psycopg.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    cursor.execute(
        "INSERT INTO users (id, email, display_name, role, password_hash, "
        "is_active) VALUES "
        "('00000000-0000-0000-0000-000000000401', 'one@example.test', "
        "'One', 'Applicant', 'hash', true), "
        "('00000000-0000-0000-0000-000000000402', 'two@example.test', "
        "'Two', 'Applicant', 'hash', true)"
    )
    cursor.execute(
        "INSERT INTO products (id, code, title, family, status) VALUES "
        "('00000000-0000-0000-0000-000000000403', 'scoped', 'Scoped', "
        "'motor', 'active')"
    )
    cursor.execute(
        "INSERT INTO product_versions (id, product_id, version, "
        "configuration, content_hash, status) VALUES "
        "('00000000-0000-0000-0000-000000000404', "
        "'00000000-0000-0000-0000-000000000403', 'v1', '{}', 'hash', "
        "'active')"
    )
    cursor.execute(
        "INSERT INTO rulebook_versions (id, product_version_id, version, "
        "rules, content_hash) VALUES "
        "('00000000-0000-0000-0000-000000000405', "
        "'00000000-0000-0000-0000-000000000404', 'v1', '{}', 'hash')"
    )
    cursor.execute(
        "INSERT INTO cases (id, applicant_user_id, product_version_id, "
        "rulebook_version_id, status, idempotency_key) VALUES "
        "('00000000-0000-0000-0000-000000000406', "
        "'00000000-0000-0000-0000-000000000401', "
        "'00000000-0000-0000-0000-000000000404', "
        "'00000000-0000-0000-0000-000000000405', 'new', 'shared-key'), "
        "('00000000-0000-0000-0000-000000000407', "
        "'00000000-0000-0000-0000-000000000402', "
        "'00000000-0000-0000-0000-000000000404', "
        "'00000000-0000-0000-0000-000000000405', 'new', 'shared-key')"
    )
    cursor.execute(
        "SELECT count(*) FROM cases WHERE idempotency_key = 'shared-key'"
    )
    assert cursor.fetchone()[0] == 2
    cursor.execute("SAVEPOINT duplicate_key")
    with pytest.raises(psycopg.errors.UniqueViolation):
        cursor.execute(
            "INSERT INTO cases (id, applicant_user_id, product_version_id, "
            "rulebook_version_id, status, idempotency_key) VALUES "
            "('00000000-0000-0000-0000-000000000408', "
            "'00000000-0000-0000-0000-000000000401', "
            "'00000000-0000-0000-0000-000000000404', "
            "'00000000-0000-0000-0000-000000000405', 'new', 'shared-key')"
        )
    cursor.execute("ROLLBACK TO SAVEPOINT duplicate_key")
    connection.rollback()
    connection.close()


# Prove PostgreSQL permits only one active version per product.
def test_only_one_active_version_per_product() -> None:
    connection = psycopg.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    cursor.execute(
        "INSERT INTO products (id, code, title, family, status) VALUES "
        "('00000000-0000-0000-0000-000000000501', 'single', 'Single', "
        "'motor', 'active')"
    )
    cursor.execute(
        "INSERT INTO product_versions (id, product_id, version, "
        "configuration, content_hash, status) VALUES "
        "('00000000-0000-0000-0000-000000000502', "
        "'00000000-0000-0000-0000-000000000501', 'v1', '{}', 'hash', "
        "'active'), "
        "('00000000-0000-0000-0000-000000000503', "
        "'00000000-0000-0000-0000-000000000501', 'v2', '{}', 'hash', "
        "'draft')"
    )
    cursor.execute("SAVEPOINT second_active")
    with pytest.raises(psycopg.errors.UniqueViolation):
        cursor.execute(
            "UPDATE product_versions SET status = 'active' WHERE id = "
            "'00000000-0000-0000-0000-000000000503'"
        )
    cursor.execute("ROLLBACK TO SAVEPOINT second_active")
    cursor.execute(
        "UPDATE product_versions SET status = 'retired' WHERE id = "
        "'00000000-0000-0000-0000-000000000502'"
    )
    cursor.execute(
        "UPDATE product_versions SET status = 'active' WHERE id = "
        "'00000000-0000-0000-0000-000000000503'"
    )
    cursor.execute(
        "SELECT count(*) FROM product_versions WHERE product_id = "
        "'00000000-0000-0000-0000-000000000501' AND status = 'active'"
    )
    assert cursor.fetchone()[0] == 1
    connection.rollback()
    connection.close()
