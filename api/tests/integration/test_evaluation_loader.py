"""Integration coverage for the explicit evaluation data loader.

The loader is exercised with an injected two-record subset of the shipped
corpus, as the operator contract allows, so these tests prove mapping,
retry, and collision behavior without loading all ninety cases.
"""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

loader = pytest.importorskip("load_evaluation_data")

from underwriteflow.evaluation.dataset import (  # noqa: E402
    load_dataset,
)

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)
UPLOAD_ROOT = Path("/data/uploads")

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


# Return every case reserved by one dataset identity.
def _reserved_cases(dataset_sha256: str) -> list[tuple[UUID, str]]:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT id, idempotency_key FROM cases "
            "WHERE idempotency_key LIKE %s",
            (f"evaluation:{dataset_sha256}:%",),
        ).fetchall()


# Count audit events of one type recorded for one dataset identity.
def _marker_count(event_type: str, dataset_sha256: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT count(*) FROM audit_events WHERE event_type = %s "
            "AND details ->> 'dataset_sha256' = %s",
            (event_type, dataset_sha256),
        ).fetchone()[0]


# Remove every row and file one loader run created for this dataset.
def _purge(dataset_sha256: str) -> None:
    case_ids = [row[0] for row in _reserved_cases(dataset_sha256)]
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


# Provide the injected subset and clean every row it reserves afterwards.
@pytest.fixture
def subset() -> Iterator[list[dict]]:
    records = _subset()
    identity = loader.records_sha256(records)
    _purge(identity)
    try:
        yield records
    finally:
        _purge(identity)


# Count rows in one business table.
def _count(table: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            f"SELECT count(*) FROM {table}"
        ).fetchone()[0]


# Given an injected corpus, when loaded, then every source value maps onto
# the existing case, submission, document, and workflow records.
@pytest.mark.asyncio
async def test_load_maps_every_source_value(subset) -> None:
    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is True
    assert result["expected_count"] == len(subset)
    assert result["created_count"] == len(subset)
    assert result["verified_count"] == len(subset)

    identity = result["dataset_sha256"]
    reserved = dict(
        (key, case_id) for case_id, key in _reserved_cases(identity)
    )
    assert len(reserved) == len(subset)
    with psycopg.connect(DATABASE_URL) as connection:
        for record in subset:
            case_id = reserved[loader.record_key(identity, record["case_id"])]
            row = connection.execute(
                "SELECT c.journey_type, v.version, p.code, c.status "
                "FROM cases c "
                "JOIN product_versions v ON v.id = c.product_version_id "
                "JOIN products p ON p.id = v.product_id WHERE c.id = %s",
                (case_id,),
            ).fetchone()
            assert row[0] == record["journey_type"]
            assert row[1] == record["configuration_version"]
            assert row[2] == record["product_code"]
            assert row[3] != "completed"

            payload = connection.execute(
                "SELECT payload -> 'application' FROM submissions "
                "WHERE case_id = %s",
                (case_id,),
            ).fetchone()[0]
            assert payload == record["workflow_input"]["payload"]

            codes = connection.execute(
                "SELECT document_code FROM documents WHERE case_id = %s "
                "ORDER BY document_code",
                (case_id,),
            ).fetchall()
            assert [row[0] for row in codes] == sorted(
                document["document_id"] for document in record["documents"]
            )

            recommendations = connection.execute(
                "SELECT count(*) FROM recommendations WHERE case_id = %s",
                (case_id,),
            ).fetchone()[0]
            assert recommendations >= 1


# Given a completed load, when the same command runs again, then nothing is
# duplicated and the load stays complete.
@pytest.mark.asyncio
async def test_repeat_load_creates_no_duplicate(subset) -> None:
    first = await loader.load_evaluation_data(records=subset)
    before = {table: _count(table) for table in BUSINESS_TABLES}

    second = await loader.load_evaluation_data(records=subset)

    assert second["created_count"] == 0
    assert second["complete"] is True
    assert second["dataset_sha256"] == first["dataset_sha256"]
    assert {table: _count(table) for table in BUSINESS_TABLES} == before
    assert (
        _marker_count("evaluation_dataset_loaded", first["dataset_sha256"])
        == 1
    )
    assert _marker_count(
        "evaluation_record_loaded", first["dataset_sha256"]
    ) == len(subset)


# Given unrelated records, when the loader runs, then they are untouched.
@pytest.mark.asyncio
async def test_unrelated_records_are_untouched(subset) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        before = connection.execute(
            "SELECT count(*) FROM cases WHERE idempotency_key NOT LIKE %s",
            ("evaluation:%",),
        ).fetchone()[0]
        users_before = connection.execute(
            "SELECT count(*) FROM users"
        ).fetchone()[0]
        active_before = connection.execute(
            "SELECT p.code, v.version FROM product_versions v "
            "JOIN products p ON p.id = v.product_id "
            "WHERE v.status = 'active' ORDER BY p.code"
        ).fetchall()

    await loader.load_evaluation_data(records=subset)

    with psycopg.connect(DATABASE_URL) as connection:
        after = connection.execute(
            "SELECT count(*) FROM cases WHERE idempotency_key NOT LIKE %s",
            ("evaluation:%",),
        ).fetchone()[0]
        users_after = connection.execute(
            "SELECT count(*) FROM users"
        ).fetchone()[0]
        active_after = connection.execute(
            "SELECT p.code, v.version FROM product_versions v "
            "JOIN products p ON p.id = v.product_id "
            "WHERE v.status = 'active' ORDER BY p.code"
        ).fetchall()

    assert after == before
    assert users_after == users_before
    assert active_after == active_before


# Given an interrupted load, when it is retried, then only missing stages
# are filled and no completion marker survives the interruption.
@pytest.mark.asyncio
async def test_interrupted_load_resumes_without_duplicating(
    subset, monkeypatch
) -> None:
    identity = loader.records_sha256(subset)
    original = loader.load_record
    calls = {"count": 0}

    # Fail the second record once, leaving the first one committed.
    async def _failing(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("synthetic interruption")
        return await original(*args, **kwargs)

    monkeypatch.setattr(loader, "load_record", _failing)

    with pytest.raises(RuntimeError):
        await loader.load_evaluation_data(records=subset)

    assert len(_reserved_cases(identity)) == 1
    assert _marker_count("evaluation_dataset_loaded", identity) == 0

    monkeypatch.setattr(loader, "load_record", original)
    retried = await loader.load_evaluation_data(records=subset)

    assert retried["complete"] is True
    assert retried["created_count"] == 1
    assert retried["resumed_count"] == 1
    assert retried["verified_count"] == len(subset)
    assert len(_reserved_cases(identity)) == len(subset)
    assert _marker_count("evaluation_dataset_loaded", identity) == 1


# Given a reserved identity whose stored record no longer matches, when the
# loader runs, then it reports a collision and overwrites nothing.
@pytest.mark.asyncio
async def test_mismatched_reserved_identity_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    case_id = dict(
        (key, value) for value, key in _reserved_cases(identity)
    )[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE submissions SET payload = jsonb_set("
            "payload, '{application,vehicle_age}', '99') WHERE case_id = %s",
            (case_id,),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    with psycopg.connect(DATABASE_URL) as connection:
        stored = connection.execute(
            "SELECT payload -> 'application' -> 'vehicle_age' "
            "FROM submissions WHERE case_id = %s",
            (case_id,),
        ).fetchone()[0]
    assert stored == 99


# Given a loaded case, when the load finishes, then no human review,
# completion, or handoff action was taken for it.
@pytest.mark.asyncio
async def test_load_never_reviews_completes_or_hands_off(subset) -> None:
    result = await loader.load_evaluation_data(records=subset)
    identity = result["dataset_sha256"]
    case_ids = [case_id for case_id, _ in _reserved_cases(identity)]

    with psycopg.connect(DATABASE_URL) as connection:
        for case_id in case_ids:
            assert (
                connection.execute(
                    "SELECT count(*) FROM handoffs WHERE case_id = %s",
                    (case_id,),
                ).fetchone()[0]
                == 0
            )
            status = connection.execute(
                "SELECT status FROM cases WHERE id = %s", (case_id,)
            ).fetchone()[0]
            assert status != "completed"
            reviewed = connection.execute(
                "SELECT count(*) FROM reviews WHERE case_id = %s",
                (case_id,),
            ).fetchone()[0]
            assert reviewed == 0
