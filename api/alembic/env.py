"""Alembic environment for the PostgreSQL business schema."""

import asyncio
import re
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from underwriteflow.persistence.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

VERSIONS_DIR = Path(__file__).resolve().parent / "versions"
NUMBERED_NAME = re.compile(r"^(\d+)_")


# Return the next free sequence number for the migration versions directory.
def next_migration_number(versions_dir: Path) -> str:
    highest = 0
    for path in versions_dir.glob("*.py"):
        match = NUMBERED_NAME.match(path.name)
        if match is not None:
            highest = max(highest, int(match.group(1)))
    return f"{highest + 1:02d}"


# Number generated migrations so revision files follow the project convention.
def number_revision(_context, _revision, directives) -> None:
    number = next_migration_number(VERSIONS_DIR)
    for directive in directives:
        directive.rev_id = number


# Configure migrations against an established synchronous connection.
def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=number_revision,
    )
    with context.begin_transaction():
        context.run_migrations()


# Run migrations through the project's asyncpg database URL.
async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy."
    )
    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)
    await connectable.dispose()


# Select offline SQL generation or the async online migration path.
def run_migrations_online() -> None:
    if context.is_offline_mode():
        context.configure(url=config.get_main_option("sqlalchemy.url"))
        with context.begin_transaction():
            context.run_migrations()
        return
    asyncio.run(run_async_migrations())


run_migrations_online()
