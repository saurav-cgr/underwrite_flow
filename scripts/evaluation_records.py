"""Per-record verification helpers for the evaluation data loader.

These helpers answer one question each: does the record already persisted
for a reserved identity match the source record exactly? They never write,
so the loader can decide between skipping, resuming, and refusing.
"""

import hashlib
import os
import sys
from typing import Any

sys.path.insert(0, os.environ.get("UNDERWRITEFLOW_SRC", "/app/src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from underwriteflow.persistence.models import (  # noqa: E402
    Document,
    Product,
    ProductVersion,
    Recommendation,
    RulebookVersion,
    Submission,
)
from underwriteflow.storage import (  # noqa: E402
    StorageValidationError,
    UploadStorage,
)

from synthetic_pdf import document_types, document_upload  # noqa: E402


class RecordCollision(Exception):
    """One reserved identity whose stored record contradicts its source."""

    # Record the safe stage and source case the collision was found at.
    def __init__(self, source_case_id: str, stage: str) -> None:
        super().__init__(f"{source_case_id}:{stage}")
        self.source_case_id = source_case_id
        self.stage = stage


# Build the deterministic bytes, filename, and type for one source document.
def rendered_document(
    document: dict[str, Any], configuration: Any
) -> tuple[str, bytes, str, str]:
    filename, content, content_type = document_upload(
        document, document_types(configuration)
    )
    return (
        filename,
        content,
        content_type,
        hashlib.sha256(content).hexdigest(),
    )


# Confirm an existing case pins the exact version and journey it claims.
async def verify_case(
    session: AsyncSession, case: Any, record: dict[str, Any]
) -> None:
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    product = (
        await session.scalar(
            select(Product).where(Product.id == product_version.product_id)
        )
        if product_version is not None
        else None
    )
    if (
        product_version is None
        or product is None
        or product.code != record["product_code"]
        or product_version.version != record["configuration_version"]
        or case.journey_type != record["journey_type"]
    ):
        raise RecordCollision(record["case_id"], "case")
    rulebook = await session.scalar(
        select(RulebookVersion).where(
            RulebookVersion.id == case.rulebook_version_id
        )
    )
    if (
        rulebook is None
        or rulebook.product_version_id != product_version.id
        or rulebook.version != record["configuration_version"]
    ):
        raise RecordCollision(record["case_id"], "rulebook")
    submission = await session.scalar(
        select(Submission).where(Submission.case_id == case.id)
    )
    stored = None
    if submission is not None:
        stored = (submission.payload or {}).get("application")
    if stored != record["workflow_input"]["payload"]:
        raise RecordCollision(record["case_id"], "application")


# Return the documents already stored for one case, keyed by document code.
#
# A null code or a code shared by two rows can never collapse into one
# entry silently: either one is a stray write that a code-keyed lookup
# would otherwise hide, so both are reported as a collision instead.
async def stored_documents(
    session: AsyncSession, case: Any, record: dict[str, Any]
) -> dict[str, Document]:
    documents = list(
        await session.scalars(
            select(Document).where(Document.case_id == case.id)
        )
    )
    codes = [document.document_code for document in documents]
    if any(code is None for code in codes) or len(set(codes)) != len(codes):
        raise RecordCollision(record["case_id"], "documents")
    return {document.document_code: document for document in documents}


# Confirm the stored document codes are exactly the source record's set.
def verify_document_set(
    record: dict[str, Any], existing: dict[str, Document]
) -> None:
    expected_codes = {
        document["document_id"] for document in record["documents"]
    }
    if set(existing) - expected_codes:
        raise RecordCollision(record["case_id"], "documents")


# Confirm one already stored document is byte-identical to its source.
def verify_document(
    record: dict[str, Any], existing: Document, content_hash: str
) -> None:
    if existing.content_hash != content_hash:
        raise RecordCollision(record["case_id"], "documents")


# Rewrite an already-verified document's bytes if a restart between loads
# lost them from an ephemeral upload volume (for example tmpfs), so a
# repeated load never reports complete over unreadable content.
def recover_document_bytes(
    storage: UploadStorage, existing: Document, content: bytes
) -> None:
    try:
        storage.read_path(existing.storage_key)
    except StorageValidationError:
        storage.restore(existing.storage_key, content)


# Confirm a processed case kept a derived result that matches its label.
async def verify_result(
    session: AsyncSession, case: Any, record: dict[str, Any]
) -> None:
    recommendation = await session.scalar(
        select(Recommendation).where(Recommendation.case_id == case.id)
    )
    if recommendation is None:
        raise RecordCollision(record["case_id"], "workflow")
    route = recommendation.route or ""
    verify_route(record, route)
    verify_derived_signals(record, recommendation.summary or {})


# Compare one derived route with its reference label, treating the needs
# information queue state as a missing-data result rather than a route.
def verify_route(record: dict[str, Any], route: str) -> None:
    expected = record["expected"]
    if route == "needs_information":
        if not expected.get("missing"):
            raise RecordCollision(record["case_id"], "workflow")
        return
    if route != expected["route"]:
        raise RecordCollision(record["case_id"], "workflow")


# Confirm a resolved case's conflict and missing-data signals both match
# their labels, independently of the final route: a route that happens to
# match cannot mask a wrong underlying conflict or missing-evidence result,
# and a queue state cannot excuse an unverified conflict signal either.
def verify_derived_signals(
    record: dict[str, Any], summary: dict[str, Any]
) -> None:
    nested = summary.get("summary") or {}
    expected = record["expected"]
    has_conflict = bool(nested.get("conflicts"))
    if has_conflict != bool(expected.get("conflict")):
        raise RecordCollision(record["case_id"], "workflow")
    has_missing = bool(nested.get("missing_information"))
    if has_missing != bool(expected.get("missing")):
        raise RecordCollision(record["case_id"], "workflow")
