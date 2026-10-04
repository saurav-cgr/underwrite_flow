"""Service for importing, tagging, and activating public regulation."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event, supersedes_details
from underwriteflow.knowledge import embedding_writer
from underwriteflow.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeError,
    KnowledgeValidationError,
)
from underwriteflow.knowledge.regulation import (
    ACCEPTED_TAGS,
    MANIFEST_NAME,
    REGULATION_LABEL,
    REGULATION_TOPIC,
    FileReport,
    load_manifest_folder,
    read_manifest,
)
from underwriteflow.knowledge.regulation_upload import store_upload
from underwriteflow.knowledge.repository import KnowledgeRepository
from underwriteflow.persistence.knowledge_models import (
    KnowledgePassage,
    KnowledgeVersion,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.providers.embedding import EmbeddingProvider


class RegulationService:
    """Own manifest import, tag acceptance, and shared activation."""

    # Configure the repository, audit trail, and embedding provider.
    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        audit_repository: AuditRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.audit = audit_repository or AuditRepository()
        self.embedding_provider = embedding_provider

    # Import the manifest folder, storing one verified upload first if given.
    async def import_regulation(
        self,
        session: AsyncSession,
        root: Path,
        actor_user_id: UUID | None = None,
        upload: UploadFile | None = None,
    ) -> tuple[KnowledgeVersion, list[FileReport]]:
        entries = read_manifest(root / MANIFEST_NAME)
        if upload is not None:
            await store_upload(
                session, root, entries, upload, self.audit, actor_user_id
            )
        loaded = load_manifest_folder(root, entries)
        for item in loaded.files:
            if item.status == "rejected":
                self._audit_rejection(
                    session,
                    item.file,
                    item.reason or "",
                    "manifest_folder",
                    actor_user_id,
                )
        # Keep refusal audits even if the draft below conflicts.
        await session.commit()
        version = await self._draft_version(
            session,
            loaded.version,
            loaded.content_hash,
            loaded.clauses,
            loaded.files,
            actor_user_id,
        )
        return version, loaded.files

    # Audit one refused regulation file without writing any bytes.
    def _audit_rejection(
        self,
        session: AsyncSession,
        filename: str,
        reason: str,
        source: str,
        actor_user_id: UUID | None,
    ) -> None:
        self.audit.append(
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

    # Create or reuse the one draft version for this manifest content.
    async def _draft_version(
        self,
        session: AsyncSession,
        version_name: str,
        content_hash: str,
        clauses: list,
        reports: list[FileReport],
        actor_user_id: UUID | None,
    ) -> KnowledgeVersion:
        existing = await self.repository.find_identity(
            session, "regulation", None, version_name
        )
        if existing is not None:
            if existing.content_hash != content_hash:
                raise KnowledgeConflictError(
                    "version identity already exists"
                )
            if await self._needs_embeddings(session, existing):
                await embedding_writer.write_embeddings(
                    session, existing.id, self.embedding_provider
                )
                await session.commit()
            return existing
        version = KnowledgeVersion(
            scope="regulation",
            product_id=None,
            version=version_name,
            content_type="public_regulation",
            status="draft",
            content_hash=content_hash,
            source={
                "kind": "manifest_import",
                "label": REGULATION_LABEL,
                "files": [
                    {
                        "file": item.file,
                        "status": item.status,
                        "reason": item.reason,
                        "clause_count": item.clause_count,
                    }
                    for item in reports
                ],
            },
            validation={"valid": True, "issues": []},
        )
        try:
            session.add(version)
            await session.flush()
            for clause in clauses:
                session.add(
                    KnowledgePassage(
                        version_id=version.id,
                        passage_key=clause.passage_key,
                        product_code=None,
                        product_lines=list(clause.product_lines),
                        topic=REGULATION_TOPIC,
                        topic_tags=[],
                        suggested_tags=list(clause.suggested_tags),
                        limits=[],
                        thresholds=[],
                        title=clause.title,
                        body=clause.body,
                        label=REGULATION_LABEL,
                        source_locator=clause.source_locator,
                    )
                )
            await session.flush()
            await embedding_writer.write_embeddings(
                session, version.id, self.embedding_provider
            )
            self.audit.append(
                session,
                build_audit_event(
                    "knowledge_version_loaded",
                    {
                        "scope": version.scope,
                        "product_code": None,
                        "version": version.version,
                        "content_hash": content_hash,
                        "passage_count": len(clauses),
                    },
                    actor_user_id=actor_user_id,
                ),
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise KnowledgeConflictError(
                "version identity already exists"
            ) from None
        return version

    # Report whether any stored passage still needs an embedding.
    async def _needs_embeddings(
        self, session: AsyncSession, version: KnowledgeVersion
    ) -> bool:
        passages = await self.repository.list_passages(session, version.id)
        return embedding_writer.needs_embeddings(
            version, passages, self.embedding_provider
        )

    # Accept administrator tags and limits on one regulation draft.
    async def accept_tags(
        self,
        session: AsyncSession,
        version_id: UUID,
        passage_key: str,
        topic_tags: list[str],
        limits: list[dict] | None,
        actor_user_id: UUID,
    ) -> KnowledgePassage:
        unknown = sorted(set(topic_tags) - ACCEPTED_TAGS)
        if unknown:
            raise KnowledgeValidationError(
                f"unknown_regulation_tag: {unknown[0]}"
            )
        version = await self.repository.find(session, version_id)
        if version is None:
            raise KnowledgeError("knowledge version not found")
        if version.scope != "regulation" or version.status != "draft":
            raise KnowledgeConflictError(
                "regulation tags are accepted on drafts only"
            )
        passage = await session.scalar(
            select(KnowledgePassage).where(
                KnowledgePassage.version_id == version_id,
                KnowledgePassage.passage_key == passage_key,
            )
        )
        if passage is None:
            raise KnowledgeError("passage not found")
        passage.topic_tags = list(topic_tags)
        # A tag-only accept must not erase limits accepted earlier.
        if limits is not None:
            passage.limits = list(limits)
        self.audit.append(
            session,
            build_audit_event(
                "regulation_tags_accepted",
                {
                    "version": version.version,
                    "passage_key": passage_key,
                    "topic_tags": list(topic_tags),
                    "limit_count": len(passage.limits),
                },
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
        return passage

    # Activate one shared regulation version for every new case.
    async def activate(
        self,
        session: AsyncSession,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> KnowledgeVersion:
        target = await self.repository.find_for_update(session, version_id)
        if target is None:
            raise KnowledgeError("knowledge version not found")
        if target.scope != "regulation":
            raise KnowledgeError("knowledge version not found")
        if target.status == "retired":
            raise KnowledgeValidationError("retired version cannot be active")
        if target.status == "active":
            return target
        try:
            siblings = await self.repository.list_active_shared(
                session, "regulation"
            )
            previous_active = next(
                (item for item in siblings if item.id != target.id), None
            )
            for sibling in siblings:
                if sibling.id != target.id:
                    sibling.status = "retired"
            await session.flush()
            target.status = "active"
            target.activated_at = datetime.now(timezone.utc)
            target.activated_by_user_id = actor_user_id
            await session.flush()
            previous_event = await self.audit.latest_event_id(
                session,
                ("knowledge_version_activated",),
                product_code=None,
            )
            self.audit.append(
                session,
                build_audit_event(
                    "knowledge_version_activated",
                    {
                        "scope": target.scope,
                        "product_code": None,
                        "version": target.version,
                        "previous_version": (
                            previous_active.version
                            if previous_active
                            else None
                        ),
                        "previous_version_id": (
                            previous_active.id
                            if previous_active
                            else None
                        ),
                        **supersedes_details(previous_event),
                    },
                    actor_user_id=actor_user_id,
                ),
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise KnowledgeConflictError(
                "another knowledge version is already active"
            ) from None
        return target
