"""Import the built-in fictional product configurations."""

import asyncio
from pathlib import Path

from sqlalchemy import select

from underwriteflow.auth.schemas import UserRole
from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.persistence.models import User
from underwriteflow.products.service import ProductService, load_configuration

CONFIGURATION_FILES = (
    "motor-private-car.yaml",
    "life-individual-term.yaml",
    "health-individual-family-floater.yaml",
)


# Import every built-in configuration through the same validated service path.
async def import_configurations(root: Path = Path("/app/product-config")) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            admin = await session.scalar(
                select(User).where(User.role == UserRole.ADMINISTRATOR.value)
            )
            for filename in CONFIGURATION_FILES:
                configuration = load_configuration((root / filename).read_text())
                await ProductService().import_configuration(
                    session, configuration, admin.id if admin else None
                )
    finally:
        await database.close()


# Start the built-in configuration import command.
def main() -> None:
    asyncio.run(import_configurations())


if __name__ == "__main__":
    main()
