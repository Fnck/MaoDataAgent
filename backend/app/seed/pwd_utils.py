"""Seed script: create initial user for DataAgent.

Usage:
    SEED_ADMIN_PASSWORD=your-password python -m app.seed.pwd_utils
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.auth import hash_password
from app.db.database import create_user, get_user_by_username, init_tables
from app.db.session import async_session_factory


async def init_pwd(username: str = "admin", password: str | None = None) -> None:
    if not password:
        password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        print(
            "ERROR: No admin password provided. "
            "Set the SEED_ADMIN_PASSWORD environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    await init_tables()

    async with async_session_factory() as session:
        existing = await get_user_by_username(session, username)
        if existing is not None:
            print(f"User '{username}' already exists, skipping")
            return

        password_hash = hash_password(password)
        try:
            user_id = await create_user(session, username, password_hash, role="admin")
            await session.commit()
            print(f"Created user '{username}' (id={user_id})")
        except Exception as e:
            await session.rollback()
            print(f"Failed to create user '{username}': {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed initial user")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    asyncio.run(init_pwd(args.username, args.password))
