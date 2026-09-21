"""Integration coverage for the evaluation loader's collision rejections.

These tests live apart from the mapping and retry suite so both files stay
under the project's 400-line limit. Each proves one reserved-record mismatch
is caught before anything is overwritten.
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

loader = pytest.importorskip("load_evaluation_data")

from fixtures.evaluation_loader import (  # noqa: E402
    DATABASE_URL,
    _default_actor,  # noqa: F401
    purge,
    reserved_cases,
    subset,
)
from underwriteflow.evaluation.dataset import load_dataset  # noqa: E402


# Provide the one shipped record whose evidence is genuinely incomplete, so
# it naturally resolves to the needs-information queue state.
@pytest.fixture
def missing_evidence_record():
    record = next(
        item
        for item in load_dataset()
        if item["case_id"] == "motor-private-car-021"
    )
    identity = loader.records_sha256([record])
    purge(identity)
    try:
        yield record
    finally:
        purge(identity)


# Given a reserved identity whose stored record no longer matches, when the
# loader runs, then it reports a collision and overwrites nothing.
@pytest.mark.asyncio
async def test_mismatched_reserved_identity_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    case_id = dict(
        (key, value) for value, key in reserved_cases(identity)
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


# Given a case whose stored product version belongs to a different product,
# when the loader runs, then it reports a collision at the case stage.
@pytest.mark.asyncio
async def test_mismatched_product_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    life_id = reserved[loader.record_key(identity, subset[1]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        life_product_version_id = connection.execute(
            "SELECT product_version_id FROM cases WHERE id = %s", (life_id,)
        ).fetchone()[0]
        connection.execute(
            "UPDATE cases SET product_version_id = %s WHERE id = %s",
            (life_product_version_id, motor_id),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "case"


# Given a case whose stored rulebook belongs to a different product version,
# when the loader runs, then it reports a collision at the rulebook stage.
@pytest.mark.asyncio
async def test_mismatched_rulebook_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    life_id = reserved[loader.record_key(identity, subset[1]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        life_rulebook_id = connection.execute(
            "SELECT rulebook_version_id FROM cases WHERE id = %s", (life_id,)
        ).fetchone()[0]
        connection.execute(
            "UPDATE cases SET rulebook_version_id = %s WHERE id = %s",
            (life_rulebook_id, motor_id),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "rulebook"


# Given a case with a stray stored document the source record never listed,
# when the loader runs, then it reports a documents-stage collision.
@pytest.mark.asyncio
async def test_extra_stored_document_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "INSERT INTO documents (id, case_id, document_code, filename, "
            "content_type, storage_key, content_hash, byte_size) VALUES "
            "(gen_random_uuid(), %s, 'stray_document', 'stray.pdf', "
            "'application/pdf', 'stray-key', 'deadbeef', 1)",
            (motor_id,),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "documents"


# Given a resolved case whose stored conflict signal contradicts its label,
# when the loader runs, then it reports a workflow-stage collision.
@pytest.mark.asyncio
async def test_mismatched_conflict_signal_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    assert subset[0]["expected"]["conflict"] is False
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE recommendations SET summary = jsonb_set(summary, "
            "'{summary,conflicts}', "
            "'[{\"field_name\": \"synthetic\"}]'::jsonb) "
            "WHERE case_id = %s",
            (motor_id,),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "workflow"


# Given a record whose product version is not persisted, when the loader
# runs, then it refuses before any case in the batch is written, even one
# ordered ahead of the missing dependency.
@pytest.mark.asyncio
async def test_missing_baseline_version_is_a_precondition_failure(
    subset,
) -> None:
    missing = dict(subset[0])
    missing["configuration_version"] = "v999-not-persisted"
    corpus = [missing, subset[1]]
    identity = loader.records_sha256(corpus)
    purge(identity)
    try:
        result = await loader.load_evaluation_data(records=corpus)

        assert result["complete"] is False
        assert result["error_code"] == loader.ERROR_PRECONDITION
        assert len(reserved_cases(identity)) == 0
    finally:
        purge(identity)


# Given a case whose route never queues for evidence, when its stored
# summary shows a missing-data signal anyway, then the loader reports a
# collision instead of trusting the route to imply nothing is missing.
@pytest.mark.asyncio
async def test_missing_signal_is_verified_independently_of_route(
    subset,
) -> None:
    assert subset[0]["expected"]["missing"] is False
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE recommendations SET summary = jsonb_set(summary, "
            "'{summary,missing_information}', "
            "'[\"synthetic_field\"]'::jsonb) WHERE case_id = %s",
            (motor_id,),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "workflow"


# Given a case genuinely queued for missing evidence, when its stored summary
# also shows a conflict the label never claims, then the loader reports a
# collision instead of skipping the conflict check for a queue-state route.
@pytest.mark.asyncio
async def test_conflict_signal_is_verified_for_needs_information_route(
    missing_evidence_record,
) -> None:
    record = missing_evidence_record
    assert record["expected"]["conflict"] is False
    await loader.load_evaluation_data(records=[record])
    identity = loader.records_sha256([record])
    case_id = reserved_cases(identity)[0][0]
    with psycopg.connect(DATABASE_URL) as connection:
        route = connection.execute(
            "SELECT route FROM recommendations WHERE case_id = %s",
            (case_id,),
        ).fetchone()[0]
        connection.execute(
            "UPDATE recommendations SET summary = jsonb_set(summary, "
            "'{summary,conflicts}', "
            "'[{\"field_name\": \"synthetic\"}]'::jsonb) "
            "WHERE case_id = %s",
            (case_id,),
        )
        connection.commit()
    assert route == "needs_information"

    result = await loader.load_evaluation_data(records=[record])

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == record["case_id"]
    assert result["stage"] == "workflow"


# Given a stored document with a null code, when the loader runs, then it
# reports a collision instead of dropping the row from its code-keyed lookup.
@pytest.mark.asyncio
async def test_null_coded_document_is_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "INSERT INTO documents (id, case_id, document_code, filename, "
            "content_type, storage_key, content_hash, byte_size) VALUES "
            "(gen_random_uuid(), %s, NULL, 'unlabeled.pdf', "
            "'application/pdf', 'unlabeled-key', 'deadbeef', 1)",
            (motor_id,),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "documents"


# Given two stored documents sharing the same code, when the loader runs,
# then it reports a collision instead of collapsing them into one entry.
@pytest.mark.asyncio
async def test_duplicate_coded_documents_are_a_collision(subset) -> None:
    await loader.load_evaluation_data(records=subset)
    identity = loader.records_sha256(subset)
    reserved = dict((key, value) for value, key in reserved_cases(identity))
    motor_id = reserved[loader.record_key(identity, subset[0]["case_id"])]
    with psycopg.connect(DATABASE_URL) as connection:
        code, content_hash = connection.execute(
            "SELECT document_code, content_hash FROM documents "
            "WHERE case_id = %s LIMIT 1",
            (motor_id,),
        ).fetchone()
        connection.execute(
            "INSERT INTO documents (id, case_id, document_code, filename, "
            "content_type, storage_key, content_hash, byte_size) VALUES "
            "(gen_random_uuid(), %s, %s, 'duplicate.pdf', "
            "'application/pdf', 'duplicate-key', %s, 1)",
            (motor_id, code, content_hash),
        )
        connection.commit()

    result = await loader.load_evaluation_data(records=subset)

    assert result["complete"] is False
    assert result["error_code"] == "evaluation_record_collision"
    assert result["source_case_id"] == subset[0]["case_id"]
    assert result["stage"] == "documents"
