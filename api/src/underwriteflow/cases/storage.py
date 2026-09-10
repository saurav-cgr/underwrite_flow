"""Local safe storage for untrusted applicant uploads."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


class StorageValidationError(ValueError):
    """Raised when an upload is outside the supported safe limits."""


@dataclass(frozen=True)
class StoredUpload:
    """Metadata returned after a safely stored upload."""

    storage_key: str
    byte_size: int
    content_hash: str


class UploadStorage:
    """Write uploads beneath a configured local volume."""

    # Configure the local upload volume root.
    def __init__(self, root: Path) -> None:
        self.root = root

    # Validate and write one upload under a generated case-scoped key.
    async def save(self, upload: UploadFile, case_id: UUID | str) -> StoredUpload:
        content_type = upload.content_type or ""
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_CONTENT_TYPES.get(content_type, set()):
            raise StorageValidationError("unsupported document type")
        content = await upload.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise StorageValidationError("document exceeds size limit")
        storage_key = f"{case_id}/{uuid4()}{suffix}"
        destination = self.root / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredUpload(
            storage_key=storage_key,
            byte_size=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
        )
