"""Bootstrap all checked-in fictional guideline corpora as drafts."""

import asyncio
from pathlib import Path

from sqlalchemy import select

from underwriteflow.auth.schemas import UserRole
from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.models import User


# Import every mounted corpus without activating any version.
async def import_corpora(root: Path = Path("/app/knowledge-config")) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            admin = await session.scalar(
                select(User).where(User.role == UserRole.ADMINISTRATOR.value)
            )
            for path in sorted(root.glob("*/*.yaml")):
                await KnowledgeService().import_guideline(
                    session,
                    path.read_text(),
                    admin.id if admin else None,
                )
    finally:
        await database.close()


# Start the built-in corpus import command.
def main() -> None:
    asyncio.run(import_corpora())


if __name__ == "__main__":
    main()
