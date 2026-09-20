"""Upload storage, missing-document derivation, and orphan-file recovery.

Split from ``test_cases.py`` so upload/storage behaviour has a dedicated
home and the original file stays under the 400-line limit.
"""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image
from pypdf import PdfWriter

from underwriteflow.cases.service import CaseService, missing_document_codes
from underwriteflow.storage import StorageValidationError, UploadStorage
from underwriteflow.persistence.models import Case, Document
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.service import load_configuration


MOTOR_CONFIGURATION = load_configuration(
    """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Synthetic vehicle age
documents:
  - code: identity_record
    title: Identity
    requirement: required
    accepted_types: [application/pdf]
  - code: inspection_photo
    title: Inspection
    requirement: conditional
    condition: {field: vehicle_age, operator: greater_than, value: 12}
    accepted_types: [image/png]
routing_rules:
  - code: standard
    condition: {field: vehicle_age, operator: greater_than, value: 0}
    route: standard
specialist_labels: [motor inspection]
"""
)


# Build a minimal synthetic PDF with the requested page count.
def synthetic_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# Build a minimal synthetic PNG image.
def synthetic_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


class FailingStorage:
    """Represent an upload volume whose file removal always fails."""

    # Fail every removal request like an unavailable volume.
    def delete(self, storage_key: str) -> None:
        raise OSError(f"synthetic storage failure: {storage_key}")


class StubSession:
    """Provide the small session surface used by document removal."""

    # Record additions, deletions, and commits without a database.
    def __init__(self, document: Document) -> None:
        self.document = document
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commits = 0

    # Return the single document this stub knows about.
    async def scalar(self, _statement: object) -> Document:
        return self.document

    # Record one scheduled row deletion.
    async def delete(self, instance: object) -> None:
        self.deleted.append(instance)

    # Record one appended row.
    def add(self, instance: object) -> None:
        self.added.append(instance)

    # Count committed transactions.
    async def commit(self) -> None:
        self.commits += 1


# Verify uploads use generated case-scoped keys and preserve content hashes.
@pytest.mark.asyncio
async def test_upload_storage_rejects_unsafe_types_and_hashes_content(
    tmp_path: Path,
) -> None:
    storage = UploadStorage(tmp_path)
    content = synthetic_pdf()
    upload = UploadFile(
        filename="../../synthetic.pdf",
        file=BytesIO(content),
        headers={"content-type": "application/pdf"},
    )

    stored = await storage.save(upload, "case-123")

    assert stored.storage_key.startswith("case-123/")
    assert ".." not in stored.storage_key
    assert stored.byte_size == len(content)
    assert stored.content_hash


# Verify the stored content type comes from the bytes, not the declaration.
@pytest.mark.asyncio
async def test_upload_storage_rejects_content_type_mismatch(
    tmp_path: Path,
) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="synthetic.pdf",
        file=BytesIO(synthetic_png()),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(StorageValidationError):
        await storage.save(upload, "case-123")


# Verify a supported declaration cannot carry an unrelated extension.
@pytest.mark.asyncio
async def test_upload_storage_rejects_extension_mismatch(
    tmp_path: Path,
) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="synthetic.pdf",
        file=BytesIO(synthetic_png()),
        headers={"content-type": "image/png"},
    )

    with pytest.raises(StorageValidationError):
        await storage.save(upload, "case-123")


# Verify unreadable bytes are refused instead of stored.
@pytest.mark.asyncio
async def test_upload_storage_rejects_unreadable_content(
    tmp_path: Path,
) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="synthetic.pdf",
        file=BytesIO(b"SYNTHETIC - FOR DEMONSTRATION ONLY"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(StorageValidationError):
        await storage.save(upload, "case-123")


# Verify the page count is calculated from the stored document bytes.
@pytest.mark.asyncio
async def test_upload_storage_computes_page_count(tmp_path: Path) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="synthetic.pdf",
        file=BytesIO(synthetic_pdf(pages=3)),
        headers={"content-type": "application/pdf"},
    )

    stored = await storage.save(upload, "case-123")

    assert stored.page_count == 3
    assert stored.content_type == "application/pdf"


# Verify stored content is resolved only from beneath the upload root.
def test_upload_storage_resolves_safe_content_paths(tmp_path: Path) -> None:
    stored = tmp_path / "case-123" / "synthetic.pdf"
    stored.parent.mkdir()
    stored.write_bytes(synthetic_pdf())
    storage = UploadStorage(tmp_path)

    assert storage.read_path("case-123/synthetic.pdf") == stored.resolve()
    with pytest.raises(StorageValidationError):
        storage.read_path("../outside.pdf")
    with pytest.raises(StorageValidationError):
        storage.read_path("case-123/missing.pdf")


# Verify a configured document code accepts only its advertised content types
# and leaves nothing on the volume when the type is refused.
@pytest.mark.asyncio
async def test_upload_storage_rejects_types_outside_the_configured_set(
    tmp_path: Path,
) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="synthetic.pdf",
        file=BytesIO(synthetic_pdf()),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(StorageValidationError):
        await storage.save(
            upload, "case-123", allowed_types={"image/jpeg", "image/png"}
        )

    assert list(tmp_path.rglob("*")) == []


# Verify missing requirements are derived from codes, not uploaded files.
def test_missing_document_codes_uses_codes_not_file_count() -> None:
    provided = ["inspection_photo"]

    missing = missing_document_codes(
        MOTOR_CONFIGURATION, provided, {"vehicle_age": 14}
    )

    assert missing == ["identity_record"]


# Verify conditional requirements drop out when their condition is unmet.
def test_missing_document_codes_ignores_unmet_conditions() -> None:
    missing = missing_document_codes(
        MOTOR_CONFIGURATION, ["identity_record"], {"vehicle_age": 2}
    )

    assert missing == []


# Verify a failed file removal leaves a recoverable orphan audit event.
@pytest.mark.asyncio
async def test_remove_document_records_orphan_when_file_removal_fails() -> None:
    case_id = uuid4()
    document = Document(
        id=uuid4(),
        case_id=case_id,
        document_code="identity_record",
        filename="synthetic.pdf",
        content_type="application/pdf",
        storage_key=f"{case_id}/synthetic.pdf",
        content_hash="synthetic-hash",
        byte_size=32,
        page_count=1,
    )
    case = Case(id=case_id, status="needs_information", journey_type="renewal")
    session = StubSession(document)
    service = CaseService(FailingStorage(), AuditRepository())

    await service.remove_document(session, case, document.id, uuid4())

    assert session.commits == 2
    assert [event.event_type for event in session.added] == [
        "document_removed",
        "document_file_orphaned",
    ]
    assert all(
        event.details["journey"] == "renewal" for event in session.added
    )
