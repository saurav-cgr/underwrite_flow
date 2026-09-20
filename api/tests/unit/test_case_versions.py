"""Unit coverage for exact product-version resolution during case creation.

These tests split out of `test_cases.py` to keep both files under the
project's 400-line limit. They run against the local synthetic stack because
version pinning is only observable against stored product versions.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fixtures.case_fixtures import (
    motor_status,
    remove_case,
    set_motor_status,
)
from fixtures.records import create_user, remove_user_with_audit
from underwriteflow.cases.schemas import CaseCreate
from underwriteflow.cases.service import CaseService, CaseValidationError
from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.evaluation.dataset import load_dataset
from underwriteflow.persistence.models import (
    Product,
    ProductVersion,
    RulebookVersion,
)


class FailingStorage:
    """Represent an upload volume whose file removal always fails."""

    # Fail every removal request like an unavailable volume.
    def delete(self, storage_key: str) -> None:
        raise OSError(f"synthetic storage failure: {storage_key}")


# Open one database session against the local synthetic stack.
@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    database = Database(get_settings().database_url)
    try:
        async with database.session_factory() as session:
            yield session
    finally:
        await database.close()


# Read one stored product version by product code and exact version.
async def _stored_version(
    session: AsyncSession, product_code: str, version: str
) -> ProductVersion:
    return await session.scalar(
        select(ProductVersion)
        .join(Product, Product.id == ProductVersion.product_id)
        .where(Product.code == product_code, ProductVersion.version == version)
    )


# Given an exact existing version, when trusted internal loading creates a
# case, then the case pins that version and its rulebook without activation.
@pytest.mark.asyncio
async def test_create_case_pins_an_exact_requested_version() -> None:
    applicant_id = create_user()
    case_id = None
    try:
        async with _session() as session:
            requested = await _stored_version(
                session, "motor-private-car", "v5"
            )
            assert requested.status != "active"
            case = await CaseService(FailingStorage()).create_case(
                session,
                applicant_id,
                CaseCreate(
                    product_code="motor-private-car",
                    idempotency_key=f"synthetic-exact-{uuid4()}",
                    journey="new_business",
                    payload={"vehicle_age": 3, "vehicle_use": "personal"},
                    document_codes=[],
                ),
                version="v5",
            )
            case_id = case.id
            rulebook = await session.scalar(
                select(RulebookVersion).where(
                    RulebookVersion.id == case.rulebook_version_id
                )
            )
            reread = await _stored_version(
                session, "motor-private-car", "v5"
            )

            assert case.product_version_id == requested.id
            assert rulebook.product_version_id == requested.id
            assert reread.status != "active"
    finally:
        if case_id is not None:
            remove_case(case_id)
        remove_user_with_audit(applicant_id)


# Return one corpus record written for an exact motor version.
def _record_for_motor(version: str) -> dict:
    return next(
        record
        for record in load_dataset()
        if record["product_code"] == "motor-private-car"
        and record["configuration_version"] == version
    )


# Activate motor v1 for one test and put every version status back, so a
# suite that left another version active cannot change this outcome.
@pytest.fixture
def active_motor_v1() -> Iterator[str]:
    found = motor_status()
    set_motor_status("active", "v1")
    try:
        yield "v1"
    finally:
        set_motor_status(found)


# Given no requested version, when normal intake creates a case, then the
# active version is still the only one selected.
@pytest.mark.asyncio
async def test_create_case_without_a_version_uses_the_active_version(
    active_motor_v1,
) -> None:
    applicant_id = create_user()
    case_id = None
    try:
        async with _session() as session:
            active = await session.scalar(
                select(ProductVersion)
                .join(Product, Product.id == ProductVersion.product_id)
                .where(
                    Product.code == "motor-private-car",
                    ProductVersion.status == "active",
                )
            )
            record = _record_for_motor(active.version)
            case = await CaseService(FailingStorage()).create_case(
                session,
                applicant_id,
                CaseCreate(
                    product_code="motor-private-car",
                    idempotency_key=f"synthetic-active-{uuid4()}",
                    journey=record["journey_type"],
                    payload=record["workflow_input"]["payload"],
                    document_codes=[],
                ),
            )
            case_id = case.id
            pinned = await session.scalar(
                select(ProductVersion).where(
                    ProductVersion.id == case.product_version_id
                )
            )

            assert pinned.id == active.id
            assert pinned.status == "active"
    finally:
        if case_id is not None:
            remove_case(case_id)
        remove_user_with_audit(applicant_id)


# Given a version that does not exist, when creation is requested, then it
# is rejected instead of falling back to the active version.
@pytest.mark.asyncio
async def test_create_case_rejects_an_unknown_requested_version() -> None:
    applicant_id = create_user()
    try:
        async with _session() as session:
            with pytest.raises(CaseValidationError):
                await CaseService(FailingStorage()).create_case(
                    session,
                    applicant_id,
                    CaseCreate(
                        product_code="motor-private-car",
                        idempotency_key=f"synthetic-unknown-{uuid4()}",
                        journey="new_business",
                        payload={"vehicle_age": 3, "vehicle_use": "personal"},
                        document_codes=[],
                    ),
                    version="v999",
                )
    finally:
        remove_user_with_audit(applicant_id)
