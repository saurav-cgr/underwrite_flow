"""Integration coverage for the explicit evaluation data loader.

The loader is exercised with an injected two-record subset of the shipped
corpus, as the operator contract allows, so these tests prove mapping,
retry, and collision behavior without loading all ninety cases.
"""

import hashlib
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

loader = pytest.importorskip("load_evaluation_data")

from fixtures.evaluation_loader import (  # noqa: E402
    ADMIN_EMAIL,
    APPLICANT_EMAIL,
    BUSINESS_TABLES,
    DATABASE_URL,
    UPLOAD_ROOT,
    _default_actor,  # noqa: F401
    actor_token,
    count,
    marker_count,
    reserved_cases,
    subset,
)


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
        (key, case_id) for case_id, key in reserved_cases(identity)
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
    before = {table: count(table) for table in BUSINESS_TABLES}

    second = await loader.load_evaluation_data(records=subset)

    assert second["created_count"] == 0
    assert second["complete"] is True
    assert second["dataset_sha256"] == first["dataset_sha256"]
    assert {table: count(table) for table in BUSINESS_TABLES} == before
    assert (
        marker_count("evaluation_dataset_loaded", first["dataset_sha256"])
        == 1
    )
    assert marker_count(
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

    assert len(reserved_cases(identity)) == 1
    assert marker_count("evaluation_dataset_loaded", identity) == 0

    monkeypatch.setattr(loader, "load_record", original)
    retried = await loader.load_evaluation_data(records=subset)

    assert retried["complete"] is True
    assert retried["created_count"] == 1
    assert retried["resumed_count"] == 1
    assert retried["verified_count"] == len(subset)
    assert len(reserved_cases(identity)) == len(subset)
    assert marker_count("evaluation_dataset_loaded", identity) == 1


# Given a completed load, when its documents' bytes are lost as an
# evaluation-API-only restart would lose an ephemeral tmpfs volume, then a
# retry recovers every byte instead of reporting a repeated complete load
# over unreadable content.
@pytest.mark.asyncio
async def test_retry_recovers_documents_lost_to_a_restart(subset) -> None:
    first = await loader.load_evaluation_data(records=subset)
    identity = first["dataset_sha256"]
    case_ids = [case_id for case_id, _ in reserved_cases(identity)]
    for case_id in case_ids:
        for path in (UPLOAD_ROOT / str(case_id)).rglob("*"):
            if path.is_file():
                path.unlink()

    retried = await loader.load_evaluation_data(records=subset)

    assert retried["complete"] is True
    assert retried["created_count"] == 0
    assert retried["resumed_count"] == len(subset)
    with psycopg.connect(DATABASE_URL) as connection:
        rows = connection.execute(
            "SELECT storage_key, content_hash FROM documents "
            "WHERE case_id = ANY(%s)",
            (case_ids,),
        ).fetchall()
    assert rows
    for storage_key, content_hash in rows:
        restored = UPLOAD_ROOT / storage_key
        assert restored.is_file()
        assert hashlib.sha256(restored.read_bytes()).hexdigest() == (
            content_hash
        )


# Given a completed load, when a stored document's bytes are corrupted in
# place (present but altered, not lost), then a retry restores the exact
# source bytes instead of reporting a repeated complete load over corrupt
# content.
@pytest.mark.asyncio
async def test_retry_restores_a_present_but_corrupted_document(
    subset,
) -> None:
    first = await loader.load_evaluation_data(records=subset)
    identity = first["dataset_sha256"]
    case_ids = [case_id for case_id, _ in reserved_cases(identity)]
    corrupted_path = None
    for case_id in case_ids:
        for path in (UPLOAD_ROOT / str(case_id)).rglob("*"):
            if path.is_file():
                path.write_bytes(b"corrupted")
                corrupted_path = path
                break
        if corrupted_path is not None:
            break
    assert corrupted_path is not None

    retried = await loader.load_evaluation_data(records=subset)

    assert retried["complete"] is True
    assert retried["created_count"] == 0
    assert retried["resumed_count"] == len(subset)
    with psycopg.connect(DATABASE_URL) as connection:
        rows = connection.execute(
            "SELECT storage_key, content_hash FROM documents "
            "WHERE case_id = ANY(%s)",
            (case_ids,),
        ).fetchall()
    assert rows
    for storage_key, content_hash in rows:
        restored = UPLOAD_ROOT / storage_key
        assert hashlib.sha256(restored.read_bytes()).hexdigest() == (
            content_hash
        )


# Given no loader actor token, when the loader runs, then it refuses before
# any business or audit row is written.
@pytest.mark.asyncio
async def test_unresolvable_actor_is_a_precondition_failure(
    subset, monkeypatch
) -> None:
    monkeypatch.delenv(loader.ACTOR_TOKEN_ENV, raising=False)
    before = {table: count(table) for table in BUSINESS_TABLES}

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == loader.ERROR_PRECONDITION
    assert {table: count(table) for table in BUSINESS_TABLES} == before


# Given a bare email in place of a signed token, when the loader runs, then
# it is refused: an email is never accepted as proof of identity.
@pytest.mark.asyncio
async def test_bare_email_is_not_accepted_as_identity(
    subset, monkeypatch
) -> None:
    monkeypatch.setenv(loader.ACTOR_TOKEN_ENV, ADMIN_EMAIL)

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == loader.ERROR_PRECONDITION


# Given an applicant identity, when named as the loader actor, then the load
# is refused because that role lacks the `evaluation:run` permission.
@pytest.mark.asyncio
async def test_applicant_actor_is_rejected(subset, monkeypatch) -> None:
    monkeypatch.setenv(loader.ACTOR_TOKEN_ENV, actor_token(APPLICANT_EMAIL))

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == loader.ERROR_PRECONDITION


# Given a completed load, when its markers are inspected, then each one
# records the authenticated actor and each case marker pins the exact
# product and rulebook version identities.
@pytest.mark.asyncio
async def test_markers_record_actor_and_pinned_versions(subset) -> None:
    result = await loader.load_evaluation_data(records=subset)
    identity = result["dataset_sha256"]

    with psycopg.connect(DATABASE_URL) as connection:
        actor_id = connection.execute(
            "SELECT id FROM users WHERE email = %s",
            (ADMIN_EMAIL,),
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT actor_user_id, details FROM audit_events "
            "WHERE event_type = %s "
            "AND details ->> 'dataset_sha256' = %s",
            ("evaluation_record_loaded", identity),
        ).fetchall()

    assert len(rows) == len(subset)
    for actor_user_id, details in rows:
        assert actor_user_id == actor_id
        assert details["product_version_id"]
        assert details["rulebook_version_id"]


# Given a completed load, when its case-lifecycle audit events are read,
# then each one attributes the authenticated loader operator, never the
# demo applicant that still owns the case.
@pytest.mark.asyncio
async def test_case_lifecycle_events_attribute_the_loader_actor(
    subset,
) -> None:
    result = await loader.load_evaluation_data(records=subset)
    identity = result["dataset_sha256"]

    with psycopg.connect(DATABASE_URL) as connection:
        actor_id = connection.execute(
            "SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,)
        ).fetchone()[0]
        applicant_id = connection.execute(
            "SELECT id FROM users WHERE email = %s", (APPLICANT_EMAIL,)
        ).fetchone()[0]
        case_ids = [case_id for case_id, _ in reserved_cases(identity)]
        rows = connection.execute(
            "SELECT event_type, actor_user_id FROM audit_events "
            "WHERE case_id = ANY(%s) "
            "AND event_type IN "
            "('case_created', 'document_uploaded', 'case_submitted')",
            (case_ids,),
        ).fetchall()

    assert len(rows) >= len(subset) * 2
    for event_type, actor_user_id in rows:
        assert actor_user_id == actor_id, event_type
        assert actor_user_id != applicant_id


# Given a loaded case, when the load finishes, then no human review,
# completion, or handoff action was taken for it.
@pytest.mark.asyncio
async def test_load_never_reviews_completes_or_hands_off(subset) -> None:
    result = await loader.load_evaluation_data(records=subset)
    identity = result["dataset_sha256"]
    case_ids = [case_id for case_id, _ in reserved_cases(identity)]

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
