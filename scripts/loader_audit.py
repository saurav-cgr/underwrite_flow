"""Actor resolution and audit-marker helpers for the evaluation loader.

Split out of `load_evaluation_data.py` to keep that file under the project
line-count limit. These helpers touch only the authenticated loader actor
and the append-only audit trail; case, document, and workflow mapping stay
in the main script.
"""

from typing import Any

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.auth.dependencies import load_authorization
from underwriteflow.auth.schemas import Permission
from underwriteflow.auth.service import AuthService
from underwriteflow.config import Settings
from underwriteflow.persistence.models import (
    AuditEvent,
    Product,
    ProductVersion,
    RulebookVersion,
    User,
)

ACTOR_TOKEN_ENV = "EVALUATION_LOADER_ACTOR_TOKEN"


# Resolve the authenticated operator identity the loader records audits as.
#
# A bare email or environment-supplied name is never accepted as identity:
# the operator must hold a real, currently valid access token, re-verified
# against the database exactly like every protected API request.
async def resolve_actor(
    session: AsyncSession, settings: Settings
) -> User | None:
    token = os.getenv(ACTOR_TOKEN_ENV)
    if not token:
        return None
    service = AuthService(
        settings.session_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        refresh_pepper=settings.refresh_token_pepper,
    )
    try:
        claims = service.read_access_token(token)
    except ValueError:
        return None
    actor = await session.scalar(
        select(User).where(User.id == claims.sub, User.is_active.is_(True))
    )
    if actor is None:
        return None
    resolved = await load_authorization(session, actor.id)
    if resolved is None:
        return None
    if (
        resolved.role_code != claims.role
        or resolved.version != claims.authz_version
    ):
        return None
    if Permission.EVALUATION_RUN.value not in resolved.permissions:
        return None
    return actor


# Confirm every product version and matching rulebook the corpus needs is
# already persisted, before any case, document, or audit row is written.
async def verify_baseline_versions(
    session: AsyncSession, corpus: list[dict[str, Any]]
) -> bool:
    pairs = {
        (record["product_code"], record["configuration_version"])
        for record in corpus
    }
    for product_code, version in pairs:
        product_version = await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(
                Product.code == product_code,
                ProductVersion.version == version,
            )
        )
        if product_version is None:
            return False
        rulebook = await session.scalar(
            select(RulebookVersion).where(
                RulebookVersion.product_version_id == product_version.id,
                RulebookVersion.version == version,
            )
        )
        if rulebook is None:
            return False
    return True


# Append one bounded marker unless this dataset already recorded it.
async def append_marker(
    session: AsyncSession,
    event_type: str,
    details: dict[str, Any],
    actor_id: Any,
    case_id: Any = None,
) -> None:
    statement = select(AuditEvent.id).where(
        AuditEvent.event_type == event_type,
        AuditEvent.details["dataset_sha256"].astext
        == details["dataset_sha256"],
    )
    if "source_case_id" in details:
        statement = statement.where(
            AuditEvent.details["source_case_id"].astext
            == details["source_case_id"]
        )
    if await session.scalar(statement) is not None:
        return
    session.add(
        build_audit_event(
            event_type, details, case_id=case_id, actor_user_id=actor_id
        )
    )
    await session.commit()
