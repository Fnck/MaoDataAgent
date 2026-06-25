from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Default: PostgreSQL via asyncpg
# Override via DATABASE_URL env var (required in production)
_DEFAULT_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/dbname",
)

_engine_kwargs: dict = {}

engine: AsyncEngine = create_async_engine(_DEFAULT_DATABASE_URL, echo=False, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session (for use as FastAPI Depends)."""
    async with async_session_factory() as session:
        yield session
