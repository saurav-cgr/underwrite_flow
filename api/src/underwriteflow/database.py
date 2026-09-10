"""Database engine lifecycle helpers."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Database:
    """Own the application's asynchronous database engine."""

    # Create an engine without opening a database connection.
    def __init__(self, database_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    # Confirm the configured database accepts a minimal query.
    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    # Release pooled connections during application shutdown.
    async def close(self) -> None:
        await self.engine.dispose()
