"""Import and lifecycle service for fictional guideline corpora."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import (
    build_audit_event,
    supersedes_details,
)
from underwriteflow.knowledge.alignment import check_alignment
from underwriteflow.knowledge.corpus import (
    CorpusValidationError,
    GuidelineCorpus,
    GuidelineSection,
    Threshold,
    load_corpus,
)
from underwriteflow.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeError,
    KnowledgeValidationError,
)
from underwriteflow.knowledge.embedding_writer import write_embeddings
from underwriteflow.knowledge.repository import KnowledgeRepository
from underwriteflow.persistence.knowledge_models import (
    KnowledgePassage,
    KnowledgeVersion,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.providers.embedding import EmbeddingProvider


# Hash normalized corpus data so formatting-only imports are idempotent.
def corpus_hash(corpus: GuidelineCorpus) -> str:
    payload = corpus.model_dump(mode="json")
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


# Convert parser failures into one safe API-facing knowledge error.
def parse_guideline(text: str) -> GuidelineCorpus:
    try:
        return load_corpus(text)
    except (CorpusValidationError, ValidationError, ValueError) as error:
        raise KnowledgeError(str(error)) from error


# Turn one typed corpus section into the JSON fields stored in a passage.
def passage_from_section(
    version_id: UUID,
    corpus: GuidelineCorpus,
    section: GuidelineSection,
) -> KnowledgePassage:
    return KnowledgePassage(
        version_id=version_id,
        passage_key=section.id,
        product_code=corpus.product_code,
        product_lines=[],
        topic=section.topic,
        topic_tags=[],
        suggested_tags=[],
        limits=[],
        thresholds=[
            item.model_dump(mode="json") for item in section.thresholds
        ],
        age_min=section.age_min,
        age_max=section.age_max,
        sum_assured_min=section.sum_assured_min,
        sum_assured_max=section.sum_assured_max,
        title=section.title,
        body=section.body,
        label=corpus.label,
    )


# Build a corpus from stored passages for activation-time revalidation.
def corpus_from_version(
    version: KnowledgeVersion,
    passages: list[KnowledgePassage],
) -> GuidelineCorpus:
    sections = [
        GuidelineSection(
            id=passage.passage_key,
            title=passage.title,
            topic=passage.topic,
            age_min=passage.age_min,
            age_max=passage.age_max,
            sum_assured_min=passage.sum_assured_min,
            sum_assured_max=passage.sum_assured_max,
            thresholds=[
                Threshold.model_validate(item) for item in passage.thresholds
            ],
            body=passage.body,
        )
        for passage in passages
    ]
    return GuidelineCorpus(
        product_code=str(version.source["product_code"]),
        version=version.version,
        aligned_product_version=str(
            version.source["aligned_product_version"]
        ),
        label=str(version.source["label"]),
        topics=sorted({section.topic for section in sections}),
        sections=sections,
    )


# Validate one corpus against its named product configuration.
async def validation_report(
    session: AsyncSession,
    repository: KnowledgeRepository,
    corpus: GuidelineCorpus,
    require_active: bool = False,
) -> dict[str, Any]:
    product_version = await repository.find_product_version(
        session,
        corpus.product_code,
        corpus.aligned_product_version,
    )
    if product_version is None:
        return {
            "valid": False,
            "issues": [
                {
                    "code": "product_version_not_found",
                    "product_code": corpus.product_code,
                    "version": corpus.aligned_product_version,
                }
            ],
        }
    if require_active and product_version.status != "active":
        active_version = await repository.active_product_version(
            session, corpus.product_code
        )
        return {
            "valid": False,
            "issues": [
                {
                    "code": "product_version_not_active",
                    "product_code": corpus.product_code,
                    "version": corpus.aligned_product_version,
                    "active_version": (
                        active_version.version if active_version else None
                    ),
                }
            ],
        }
    configuration = ProductConfiguration.model_validate(
        product_version.configuration
    )
    return check_alignment(corpus, configuration)


class KnowledgeService:
    """Own immutable import, activation, and retirement behavior."""

    # Configure knowledge persistence and append-only audit recording.
    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        audit_repository: AuditRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.audit = audit_repository or AuditRepository()
        self.embedding_provider = embedding_provider

    # Validate a guideline without writing it to PostgreSQL.
    async def validate(
        self, session: AsyncSession, text: str
    ) -> tuple[GuidelineCorpus, dict[str, Any]]:
        corpus = parse_guideline(text)
        return corpus, await validation_report(session, self.repository, corpus)

    # Import one validated or invalid draft with immutable identity handling.
    async def import_guideline(
        self,
        session: AsyncSession,
        text: str,
        actor_user_id: UUID | None = None,
    ) -> KnowledgeVersion:
        corpus = parse_guideline(text)
        product = await self.repository.find_product(
            session, corpus.product_code
        )
        if product is None:
            raise KnowledgeError("product not found")
        content_hash = corpus_hash(corpus)
        existing = await self.repository.find_identity(
            session, "guideline", product.id, corpus.version
        )
        if existing is not None:
            if existing.content_hash != content_hash:
                raise KnowledgeConflictError("version identity already exists")
            passages = await self.repository.list_passages(
                session, existing.id
            )
            if any(passage.embedding is None for passage in passages):
                await write_embeddings(
                    session,
                    existing.id,
                    self.embedding_provider,
                )
                await session.commit()
            return existing
        report = await validation_report(session, self.repository, corpus)
        version = KnowledgeVersion(
            scope="guideline",
            product_id=product.id,
            version=corpus.version,
            content_type="synthetic_guidance",
            status="draft",
            content_hash=content_hash,
            source={
                "kind": "api_import",
                "product_code": corpus.product_code,
                "aligned_product_version": corpus.aligned_product_version,
                "label": corpus.label,
            },
            validation=report,
        )
        try:
            session.add(version)
            await session.flush()
            for section in corpus.sections:
                session.add(passage_from_section(version.id, corpus, section))
            await session.flush()
            await write_embeddings(
                session,
                version.id,
                self.embedding_provider,
            )
            self.audit.append(
                session,
                build_audit_event(
                    "knowledge_version_loaded",
                    {
                        "scope": version.scope,
                        "product_code": corpus.product_code,
                        "version": version.version,
                        "content_hash": content_hash,
                        "passage_count": len(corpus.sections),
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

    # Convert one persisted version into its response-safe summary.
    async def summary(
        self,
        session: AsyncSession,
        version: KnowledgeVersion,
        product_code: str | None = None,
    ) -> dict[str, Any]:
        passage_count = await self.repository.count_passages(
            session, version.id
        )
        return {
            "id": version.id,
            "scope": version.scope,
            "product_code": product_code,
            "version": version.version,
            "status": version.status,
            "content_type": version.content_type,
            "passage_count": passage_count,
            "validation": version.validation,
            "activated_at": version.activated_at,
        }

    # Activate one draft after checking alignment against the active product.
    async def activate(
        self,
        session: AsyncSession,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> KnowledgeVersion:
        target = await self.repository.find_for_update(session, version_id)
        if target is None:
            raise KnowledgeError("knowledge version not found")
        if target.status == "retired":
            raise KnowledgeValidationError("retired version cannot be active")
        if target.status == "active":
            return target
        product = await self.repository.find_product_by_id(
            session, target.product_id
        )
        if product is None:
            raise KnowledgeValidationError("knowledge product not found")
        passages = await self.repository.list_passages(session, target.id)
        corpus = corpus_from_version(target, passages)
        report = await validation_report(
            session, self.repository, corpus, require_active=True
        )
        target.validation = report
        if not report["valid"]:
            await session.rollback()
            raise KnowledgeValidationError(json.dumps(report, sort_keys=True))
        try:
            siblings = await self.repository.list_active_for_product(
                session, target.product_id
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
                product_code=product.code,
            )
            self.audit.append(
                session,
                build_audit_event(
                    "knowledge_version_activated",
                    {
                        "scope": target.scope,
                        "product_code": product.code,
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

    # Retire one active or draft version without activating a replacement.
    async def retire(
        self,
        session: AsyncSession,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> KnowledgeVersion:
        target = await self.repository.find_for_update(session, version_id)
        if target is None:
            raise KnowledgeError("knowledge version not found")
        if target.status == "retired":
            return target
        target.status = "retired"
        product_code = None
        if target.product_id is not None:
            product = await self.repository.find_product_by_id(
                session, target.product_id
            )
            product_code = product.code if product else None
        self.audit.append(
            session,
            build_audit_event(
                "knowledge_version_retired",
                {
                    "scope": target.scope,
                    "product_code": product_code,
                    "version": target.version,
                },
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
        return target
