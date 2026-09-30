"""SQLAlchemy queries for knowledge versions and their passages."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.knowledge_models import (
    KnowledgePassage,
    KnowledgeVersion,
)
from underwriteflow.persistence.models import Product, ProductVersion


class KnowledgeRepository:
    """Keep knowledge persistence queries out of service and API code."""

    # Find a product by its stable product code.
    async def find_product(
        self, session: AsyncSession, product_code: str
    ) -> Product | None:
        return await session.scalar(
            select(Product).where(Product.code == product_code)
        )

    # Find one product by its database identifier.
    async def find_product_by_id(
        self, session: AsyncSession, product_id: UUID
    ) -> Product | None:
        return await session.get(Product, product_id)

    # Find one active product configuration by code.
    async def active_product_version(
        self, session: AsyncSession, product_code: str
    ) -> ProductVersion | None:
        return await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(
                Product.code == product_code,
                ProductVersion.status == "active",
            )
        )

    # Find one named product configuration without requiring active status.
    async def find_product_version(
        self,
        session: AsyncSession,
        product_code: str,
        version: str,
    ) -> ProductVersion | None:
        return await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(
                Product.code == product_code,
                ProductVersion.version == version,
            )
        )

    # Find one knowledge identity for idempotent import handling.
    async def find_identity(
        self,
        session: AsyncSession,
        scope: str,
        product_id: UUID | None,
        version: str,
    ) -> KnowledgeVersion | None:
        statement = select(KnowledgeVersion).where(
            KnowledgeVersion.scope == scope,
            KnowledgeVersion.version == version,
        )
        if product_id is None:
            statement = statement.where(KnowledgeVersion.product_id.is_(None))
        else:
            statement = statement.where(
                KnowledgeVersion.product_id == product_id
            )
        return await session.scalar(statement)

    # Lock one knowledge version before an activation or retirement.
    async def find_for_update(
        self, session: AsyncSession, version_id: UUID
    ) -> KnowledgeVersion | None:
        return await session.scalar(
            select(KnowledgeVersion)
            .where(KnowledgeVersion.id == version_id)
            .with_for_update()
        )

    # Read one knowledge version without locking ordinary administrator views.
    async def find(
        self, session: AsyncSession, version_id: UUID
    ) -> KnowledgeVersion | None:
        return await session.scalar(
            select(KnowledgeVersion).where(KnowledgeVersion.id == version_id)
        )

    # List versions newest first, optionally scoped to one product.
    async def list_versions(
        self,
        session: AsyncSession,
        scope: str | None = None,
        product_code: str | None = None,
    ) -> list[tuple[KnowledgeVersion, str | None, int]]:
        statement = (
            select(
                KnowledgeVersion,
                Product.code,
                func.count(KnowledgePassage.id),
            )
            .outerjoin(Product, Product.id == KnowledgeVersion.product_id)
            .outerjoin(
                KnowledgePassage,
                KnowledgePassage.version_id == KnowledgeVersion.id,
            )
            .where(
                scope is None or KnowledgeVersion.scope == scope,
                product_code is None or Product.code == product_code,
            )
            .group_by(KnowledgeVersion.id, Product.code)
            .order_by(
                KnowledgeVersion.created_at.desc(),
                KnowledgeVersion.version.desc(),
            )
        )
        rows = await session.execute(statement)
        return [(version, code, int(count)) for version, code, count in rows]

    # Load one passage page in stable source-file order.
    async def list_passages(
        self,
        session: AsyncSession,
        version_id: UUID,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[KnowledgePassage]:
        statement = (
            select(KnowledgePassage)
            .where(KnowledgePassage.version_id == version_id)
            .order_by(KnowledgePassage.passage_key)
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await session.scalars(statement)
        return list(result)

    # Count passages without loading their bodies for summary responses.
    async def count_passages(
        self, session: AsyncSession, version_id: UUID
    ) -> int:
        count = await session.scalar(
            select(func.count(KnowledgePassage.id)).where(
                KnowledgePassage.version_id == version_id
            )
        )
        return int(count or 0)

    # List active knowledge versions for one product.
    async def list_active_for_product(
        self, session: AsyncSession, product_id: UUID
    ) -> list[KnowledgeVersion]:
        result = await session.scalars(
            select(KnowledgeVersion).where(
                KnowledgeVersion.product_id == product_id,
                KnowledgeVersion.status == "active",
            )
        )
        return list(result)

    # List active versions of one shared scope that no product owns.
    async def list_active_shared(
        self, session: AsyncSession, scope: str
    ) -> list[KnowledgeVersion]:
        result = await session.scalars(
            select(KnowledgeVersion).where(
                KnowledgeVersion.scope == scope,
                KnowledgeVersion.product_id.is_(None),
                KnowledgeVersion.status == "active",
            )
        )
        return list(result)
