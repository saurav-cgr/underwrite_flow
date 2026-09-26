"""Shared database and volume helpers for the evaluation loader suites.

The loader's mapping, retry, and production suites all need the same reads
and the same cleanup, so they live here instead of being duplicated or
imported across test modules.
"""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import psycopg
import pytest

from fixtures.auth import app_service

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
loader = pytest.importorskip("load_evaluation_data")

from underwriteflow.evaluation.dataset import load_dataset  # noqa: E402

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)
UPLOAD_ROOT = Path("/data/uploads")

ADMIN_EMAIL = "administrator@synthetic.test"
APPLICANT_EMAIL = "applicant@synthetic.test"

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


# Return every case reserved by one dataset identity.
def reserved_cases(dataset_sha256: str) -> list[tuple[UUID, str]]:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT id, idempotency_key FROM cases "
            "WHERE idempotency_key LIKE %s",
            (f"evaluation:{dataset_sha256}:%",),
        ).fetchall()


# Count audit events of one type recorded for one dataset identity.
def marker_count(event_type: str, dataset_sha256: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT count(*) FROM audit_events WHERE event_type = %s "
            "AND details ->> 'dataset_sha256' = %s",
            (event_type, dataset_sha256),
        ).fetchone()[0]


# Count rows in one table.
def count(table: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            f"SELECT count(*) FROM {table}"
        ).fetchone()[0]


# Mint a real access token for one seeded user's current DB authorization.
def actor_token(email: str) -> str | None:
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT u.id, r.code FROM users u "
            "JOIN user_role_mappings m ON m.user_id = u.id "
            "JOIN roles r ON r.id = m.role_id AND r.is_active "
            "WHERE u.email = %s AND u.is_active",
            (email,),
        ).fetchone()
        if row is None:
            return None
        user_id, role_code = row
        permissions = [
            code
            for (code,) in connection.execute(
                "SELECT p.code FROM role_permissions rp "
                "JOIN permissions p ON p.id = rp.permission_id "
                "JOIN roles r ON r.id = rp.role_id "
                "WHERE r.code = %s",
                (role_code,),
            ).fetchall()
        ]
    return app_service().issue_access_token(
        user_id, role_code, sorted(permissions)
    )


# Count the files currently stored under the local upload volume.
def upload_file_count() -> int:
    if not UPLOAD_ROOT.exists():
        return 0
    return sum(1 for path in UPLOAD_ROOT.rglob("*") if path.is_file())


# Remove every row and file one loader run created for this dataset.
def purge(dataset_sha256: str) -> None:
    case_ids = [row[0] for row in reserved_cases(dataset_sha256)]
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE audit_events DISABLE TRIGGER "
                "audit_events_append_only"
            )
            try:
                for case_id in case_ids:
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
                        "DELETE FROM audit_events WHERE case_id = %s",
                        (case_id,),
                    )
                    for table in BUSINESS_TABLES[::-1]:
                        column = "id" if table == "cases" else "case_id"
                        cursor.execute(
                            f"DELETE FROM {table} WHERE {column} = %s",
                            (case_id,),
                        )
                cursor.execute(
                    "DELETE FROM audit_events "
                    "WHERE details ->> 'dataset_sha256' = %s",
                    (dataset_sha256,),
                )
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events ENABLE TRIGGER "
                    "audit_events_append_only"
                )
    for case_id in case_ids:
        shutil.rmtree(UPLOAD_ROOT / str(case_id), ignore_errors=True)


# Select one small, product-diverse subset of the authoritative corpus.
def _subset() -> list[dict]:
    records = load_dataset()
    motor = next(
        record
        for record in records
        if record["product_code"] == "motor-private-car"
    )
    life = next(
        record
        for record in records
        if record["product_code"] == "life-individual-term"
    )
    return [motor, life]


# Provide the injected subset and clean every row it reserves afterwards.
@pytest.fixture
def subset() -> Iterator[list[dict]]:
    records = _subset()
    identity = loader.records_sha256(records)
    purge(identity)
    try:
        yield records
    finally:
        purge(identity)


# Attribute every load in a loader suite to a real administrator token
# unless a test overrides or clears it to exercise a rejection path.
@pytest.fixture(autouse=True)
def _default_actor(monkeypatch) -> None:
    monkeypatch.setenv(loader.ACTOR_TOKEN_ENV, actor_token(ADMIN_EMAIL))
