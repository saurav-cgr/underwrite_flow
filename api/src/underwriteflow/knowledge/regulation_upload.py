"""Stream one approved regulation upload into the manifest folder."""

import hashlib
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.knowledge.errors import KnowledgeValidationError
from underwriteflow.knowledge.regulation import ManifestEntry
from underwriteflow.persistence.repositories import AuditRepository

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
PARTIAL_SUFFIX = ".part"


# Stream one upload to disk, then keep it only if its hash is approved.
async def store_upload(
    session: AsyncSession,
    root: Path,
    entries: list[ManifestEntry],
    upload: UploadFile,
    audit: AuditRepository,
    actor_user_id: UUID | None,
) -> None:
    name = Path(upload.filename or "").name
    partial = root / f"upload-{uuid4().hex}{PARTIAL_SUFFIX}"
    hasher = hashlib.sha256()
    size = 0
    try:
        with partial.open("wb") as handle:
            while True:
                chunk = await upload.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise KnowledgeValidationError(
                        "regulation_upload_too_large"
                    )
                hasher.update(chunk)
                handle.write(chunk)
    except KnowledgeValidationError:
        partial.unlink(missing_ok=True)
        await _audit_rejection(
            session, audit, name, "too_large", "upload", actor_user_id
        )
        # Commit the refusal on its own, before the request fails.
        await session.commit()
        raise
    except OSError as error:
        partial.unlink(missing_ok=True)
        raise KnowledgeValidationError(
            "regulation_upload_unwritable"
        ) from error
    digest = hasher.hexdigest()
    entry = next((item for item in entries if item.sha256 == digest), None)
    if entry is None:
        partial.unlink(missing_ok=True)
        reason = (
            "checksum_mismatch"
            if any(item.file == name for item in entries)
            else "not_listed"
        )
        await _audit_rejection(
            session, audit, name, reason, "upload", actor_user_id
        )
        await session.commit()
        raise KnowledgeValidationError("regulation_upload_rejected")
    try:
        os.replace(partial, root / entry.file)
    except OSError as error:
        partial.unlink(missing_ok=True)
        raise KnowledgeValidationError(
            "regulation_upload_unwritable"
        ) from error
    audit.append(
        session,
        build_audit_event(
            "regulation_file_stored",
            {
                "file": entry.file,
                "document_id": entry.id,
                "sha256": digest,
                "size": size,
            },
            actor_user_id=actor_user_id,
        ),
    )


# Audit one refused regulation file without writing any bytes.
async def _audit_rejection(
    session: AsyncSession,
    audit: AuditRepository,
    filename: str,
    reason: str,
    source: str,
    actor_user_id: UUID | None,
) -> None:
    audit.append(
        session,
        build_audit_event(
            "regulation_file_rejected",
            {
                "file": Path(filename).name,
                "reason": reason,
                "source": source,
            },
            actor_user_id=actor_user_id,
        ),
    )
