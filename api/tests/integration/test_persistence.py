from uuid import UUID

import psycopg
import pytest


# Prove version pins persist and audit rows reject mutation.
def test_version_pins_and_audit_events_are_immutable() -> None:
    connection = psycopg.connect("postgresql://underwriteflow:synthetic-local-password@db:5432/underwriteflow")
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    cursor.execute("INSERT INTO users (id, email, display_name, role, password_hash, is_active) VALUES ('00000000-0000-0000-0000-000000000001', 'synthetic@example.test', 'Synthetic User', 'Applicant', 'hash', true)")
    cursor.execute("INSERT INTO products (id, code, title, family, status) VALUES ('00000000-0000-0000-0000-000000000002', 'synthetic', 'Synthetic', 'motor', 'active')")
    cursor.execute("INSERT INTO product_versions (id, product_id, version, configuration, content_hash, status) VALUES ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', 'v1', '{}', 'hash', 'active')")
    cursor.execute("INSERT INTO rulebook_versions (id, product_version_id, version, rules, content_hash) VALUES ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000003', 'v1', '{}', 'hash')")
    cursor.execute("INSERT INTO cases (id, applicant_user_id, product_version_id, rulebook_version_id, status) VALUES ('00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004', 'new')")
    cursor.execute("SELECT product_version_id FROM cases WHERE id = '00000000-0000-0000-0000-000000000005'")
    assert cursor.fetchone()[0] == UUID("00000000-0000-0000-0000-000000000003")
    cursor.execute("INSERT INTO audit_events (id, event_type, details) VALUES ('00000000-0000-0000-0000-000000000006', 'created', '{}')")
    cursor.execute("SAVEPOINT audit_mutation")
    with pytest.raises(psycopg.errors.RaiseException):
        cursor.execute("UPDATE audit_events SET event_type = 'changed'")
    cursor.execute("ROLLBACK TO SAVEPOINT audit_mutation")
    connection.rollback()
    connection.close()
