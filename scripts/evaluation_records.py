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
    ProductVersion,
    Recommendation,
    Submission,
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
    if (
        product_version is None
        or product_version.version != record["configuration_version"]
        or case.journey_type != record["journey_type"]
    ):
        raise RecordCollision(record["case_id"], "case")
    submission = await session.scalar(
        select(Submission).where(Submission.case_id == case.id)
    )
    stored = None
    if submission is not None:
        stored = (submission.payload or {}).get("application")
    if stored != record["workflow_input"]["payload"]:
        raise RecordCollision(record["case_id"], "application")


# Return the documents already stored for one case, keyed by document code.
async def stored_documents(
    session: AsyncSession, case: Any
) -> dict[str, Document]:
    documents = await session.scalars(
        select(Document).where(Document.case_id == case.id)
    )
    return {
        document.document_code: document
        for document in documents
        if document.document_code
    }


# Confirm one already stored document is byte-identical to its source.
def verify_document(
    record: dict[str, Any], existing: Document, content_hash: str
) -> None:
    if existing.content_hash != content_hash:
        raise RecordCollision(record["case_id"], "documents")


# Confirm a processed case kept a derived result that matches its label.
async def verify_result(
    session: AsyncSession, case: Any, record: dict[str, Any]
) -> None:
    recommendation = await session.scalar(
        select(Recommendation).where(Recommendation.case_id == case.id)
    )
    if recommendation is None:
        raise RecordCollision(record["case_id"], "workflow")
    verify_route(record, recommendation.route or "")


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
