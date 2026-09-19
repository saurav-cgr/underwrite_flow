"""PostgreSQL checkpoint lifecycle for resumable workflow runs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


# Open the supported LangGraph PostgreSQL saver against the existing schema.
@asynccontextmanager
async def postgres_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    connection_url = database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )
    async with AsyncPostgresSaver.from_conn_string(
        connection_url
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
