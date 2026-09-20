"""Integration coverage for the loader's fail-closed production refusal.

These tests live apart from the mapping and retry suite so both files stay
under the project's 400-line limit. They prove production writes nothing at
all and leaves the common baseline usable.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

loader = pytest.importorskip("load_evaluation_data")

from fixtures.evaluation_loader import (  # noqa: E402
    BUSINESS_TABLES,
    DATABASE_URL,
    count,
    marker_count,
    purge,
    reserved_cases,
    upload_file_count,
)
from underwriteflow.config import Settings  # noqa: E402
from underwriteflow.evaluation.dataset import load_dataset  # noqa: E402


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


# Count every checkpoint row the workflow could have written.
def _checkpointcount() -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT count(*) FROM checkpoints"
        ).fetchone()[0]


# Count every audit event, including the loader's own markers.
def _auditcount() -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT count(*) FROM audit_events"
        ).fetchone()[0]


# Given production, when the loader runs, then it writes no business row,
# checkpoint, audit event, or upload file, and the baseline stays usable.
@pytest.mark.asyncio
async def test_production_load_writes_nothing(subset) -> None:
    before = {table: count(table) for table in BUSINESS_TABLES}
    before["checkpoints"] = _checkpointcount()
    before["audit_events"] = _auditcount()
    before["upload_files"] = upload_file_count()

    result = await loader.load_evaluation_data(
        settings=Settings(_env_file=None, environment_mode="production"),
        records=subset,
    )

    assert result == {
        "environment": "production",
        "complete": False,
        "error_code": "evaluation_load_forbidden",
    }
    after = {table: count(table) for table in BUSINESS_TABLES}
    after["checkpoints"] = _checkpointcount()
    after["audit_events"] = _auditcount()
    after["upload_files"] = upload_file_count()
    assert after == before
    assert reserved_cases(loader.records_sha256(subset)) == []


# Given production, when the loader refuses, then the common baseline is
# still present and usable for the three demo identities.
@pytest.mark.asyncio
async def test_production_refusal_leaves_the_baseline_usable(subset) -> None:
    await loader.load_evaluation_data(
        settings=Settings(_env_file=None, environment_mode="production"),
        records=subset,
    )

    with psycopg.connect(DATABASE_URL) as connection:
        accounts = connection.execute(
            "SELECT count(*) FROM users WHERE is_active AND email IN "
            "('applicant@synthetic.test', 'underwriter@synthetic.test', "
            "'administrator@synthetic.test')"
        ).fetchone()[0]
        versions = connection.execute(
            "SELECT count(*) FROM product_versions"
        ).fetchone()[0]

    assert accounts == 3
    assert versions >= 10
