"""Insert-once knowledge version pins for case processing."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.persistence.knowledge_models import (
    CaseKnowledgePin,
    KnowledgeVersion,
)
from underwriteflow.persistence.models import Case, Product, ProductVersion


# Pin the active guideline version once, retaining null when none exists.
async def pin_case_knowledge(
    session: AsyncSession, case: Case, actor_user_id: UUID
) -> CaseKnowledgePin:
    product = await session.scalar(
        select(Product)
        .join(ProductVersion, ProductVersion.product_id == Product.id)
        .where(ProductVersion.id == case.product_version_id)
    )
    guideline_id = None
    if product is not None:
        guideline_id = await session.scalar(
            select(KnowledgeVersion.id).where(
                KnowledgeVersion.scope == "guideline",
                KnowledgeVersion.product_id == product.id,
                KnowledgeVersion.status == "active",
            )
        )
    statement = (
        insert(CaseKnowledgePin)
        .values(
            case_id=case.id,
            guideline_version_id=guideline_id,
            regulation_version_id=None,
        )
        .on_conflict_do_nothing(index_elements=[CaseKnowledgePin.case_id])
    )
    result = await session.execute(statement)
    if result.rowcount:
        event = build_audit_event(
            "case_guidance_pinned",
            {
                "case_id": case.id,
                "guideline_version_id": guideline_id,
                "regulation_version_id": None,
            },
            case_id=case.id,
            actor_user_id=actor_user_id,
        )
        session.add(event)
    pin = await session.scalar(
        select(CaseKnowledgePin).where(
            CaseKnowledgePin.case_id == case.id
        )
    )
    if pin is None:
        raise RuntimeError("case knowledge pin was not created")
    return pin
