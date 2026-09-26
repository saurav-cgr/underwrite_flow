"""Persistence queries for product configurations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import Product, ProductVersion


class ProductRepository:
    """Keep product persistence queries out of API handlers."""

    # Find one product by its stable code.
    async def find_product(
        self,
        session: AsyncSession,
        code: str,
    ) -> Product | None:
        return await session.scalar(select(Product).where(Product.code == code))

    # Lock one product row so concurrent activation changes serialize.
    async def find_product_for_update(
        self, session: AsyncSession, code: str
    ) -> Product | None:
        return await session.scalar(
            select(Product).where(Product.code == code).with_for_update()
        )

    # Find one version belonging to a stable product code.
    async def find_version(
        self, session: AsyncSession, code: str, version: str
    ) -> ProductVersion | None:
        return await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(Product.code == code, ProductVersion.version == version)
        )

    # List product versions in stable newest-first order.
    async def list_versions(
        self, session: AsyncSession, code: str
    ) -> list[ProductVersion]:
        result = await session.scalars(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(Product.code == code)
            .order_by(
                ProductVersion.created_at.desc(),
                ProductVersion.version.desc(),
            )
        )
        return list(result)

    # Find all versions for one product to replace its active version.
    async def list_product_versions(
        self, session: AsyncSession, product_id: UUID
    ) -> list[ProductVersion]:
        result = await session.scalars(
            select(ProductVersion).where(
                ProductVersion.product_id == product_id
            )
        )
        return list(result)
