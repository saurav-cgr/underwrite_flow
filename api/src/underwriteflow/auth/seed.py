"""Seed helpers for fictional role-based demo users."""

import asyncio
from collections.abc import Mapping
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.schemas import UserRole
from underwriteflow.auth.service import AuthService
from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.persistence.models import User

DEMO_USERS: tuple[tuple[str, str, UserRole], ...] = (
    ("applicant@synthetic.test", "Synthetic Applicant", UserRole.APPLICANT),
    (
        "underwriter@synthetic.test",
        "Synthetic Underwriter",
        UserRole.UNDERWRITER,
    ),
    (
        "administrator@synthetic.test",
        "Synthetic Administrator",
        UserRole.ADMINISTRATOR,
    ),
)


# Add missing fictional demo users using caller-supplied passwords.
async def seed_demo_users(
    session: AsyncSession,
    passwords: Mapping[UserRole, str],
    auth: AuthService,
) -> list[User]:
    users: list[User] = []
    for email, display_name, role in DEMO_USERS:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            users.append(existing)
            continue
        if role not in passwords or not passwords[role]:
            raise ValueError(f"missing password for {role.value}")
        user = User(
            email=email,
            display_name=display_name,
            role=role.value,
            password_hash=auth.hash_password(passwords[role]),
            is_active=True,
        )
        session.add(user)
        users.append(user)
    await session.commit()
    return users


# Run the seed helper with passwords supplied only through the environment.
async def run_seed() -> None:
    settings = get_settings()
    passwords = {
        UserRole.APPLICANT: os.getenv("DEMO_APPLICANT_PASSWORD", ""),
        UserRole.UNDERWRITER: os.getenv("DEMO_UNDERWRITER_PASSWORD", ""),
        UserRole.ADMINISTRATOR: os.getenv("DEMO_ADMINISTRATOR_PASSWORD", ""),
    }
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            users = await seed_demo_users(
                session,
                passwords,
                AuthService(settings.session_secret),
            )
            if len(users) != len(DEMO_USERS):
                raise RuntimeError("demo user seed is incomplete")
    finally:
        await database.close()


# Start the environment-driven seed command.
def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
