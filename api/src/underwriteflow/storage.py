"""Local safe storage for untrusted applicant uploads."""

import hashlib
from collections.abc import Collection
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image
from pypdf import PdfReader

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_PAGES = 50
ALLOWED_SUFFIXES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}
SUPPORTED_CONTENT_TYPES = frozenset(ALLOWED_SUFFIXES)
MAGIC_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class StorageValidationError(ValueError):
    """Raised when an upload is outside the supported safe limits."""


@dataclass(frozen=True)
class StoredUpload:
    """Metadata returned after a safely stored upload."""

    storage_key: str
    byte_size: int
    content_hash: str
    content_type: str
    page_count: int


# Identify a supported content type from the uploaded bytes alone.
def detect_content_type(content: bytes) -> str | None:
    for signature, content_type in MAGIC_SIGNATURES:
        if content.startswith(signature):
            return content_type
    return None


# Count the pages of one supported document from its stored bytes.
def count_pages(content: bytes, content_type: str) -> int:
    # Uploaded bytes are untrusted, so any parser failure is a client error.
    try:
        if content_type == "application/pdf":
            return len(PdfReader(BytesIO(content)).pages)
        with Image.open(BytesIO(content)) as image:
            return int(getattr(image, "n_frames", 1))
    except Exception as error:
        raise StorageValidationError(
            "document content is unreadable"
        ) from error


class UploadStorage:
    """Write uploads beneath a configured local volume."""

    # Configure the local upload volume root.
    def __init__(self, root: Path) -> None:
        self.root = root

    # Validate and write one upload under a generated case-scoped key.
    async def save(
        self,
        upload: UploadFile,
        case_id: UUID | str,
        allowed_types: Collection[str] | None = None,
    ) -> StoredUpload:
        declared = upload.content_type or ""
        suffix = Path(upload.filename or "").suffix.lower()
        content = await upload.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise StorageValidationError("document exceeds size limit")
        detected = detect_content_type(content)
        if detected is None:
            raise StorageValidationError("unsupported document type")
        if detected != declared:
            raise StorageValidationError(
                "document type does not match its content"
            )
        if suffix not in ALLOWED_SUFFIXES[detected]:
            raise StorageValidationError(
                "document extension does not match its content"
            )
        # Refuse a type the document code does not accept before any byte of
        # the upload reaches the volume.
        if allowed_types is not None and detected not in allowed_types:
            raise StorageValidationError(
                "document type is not accepted for this document code"
            )
        page_count = count_pages(content, detected)
        if not 1 <= page_count <= MAX_DOCUMENT_PAGES:
            raise StorageValidationError("document page limit exceeded")
        storage_key = f"{case_id}/{uuid4()}{suffix}"
        destination = self.root / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredUpload(
            storage_key=storage_key,
            byte_size=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
            content_type=detected,
            page_count=page_count,
        )

    # Remove one generated upload key without permitting path traversal.
    def delete(self, storage_key: str) -> None:
        destination = (self.root / storage_key).resolve()
        if self.root.resolve() not in destination.parents:
            raise StorageValidationError("invalid document storage key")
        destination.unlink(missing_ok=True)
