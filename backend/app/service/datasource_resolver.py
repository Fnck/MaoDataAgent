from __future__ import annotations

import contextvars
import logging

logger = logging.getLogger(__name__)

# Context variable storing the tenant_id for the current request/tool execution
_current_tenant_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def set_current_tenant_id(tenant_id: int) -> None:
    """Set the tenant_id for the current context."""
    _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> int | None:
    """Get the tenant_id from the current context."""
    return _current_tenant_id.get()


async def resolve_active_datasource() -> dict | None:
    """Resolve the active datasource config for the current tenant context.

    Returns a dict with keys: id, name, dsn, db_type.
    """
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        logger.debug("No tenant context, using default PostgreSQL datasource")
        return _make_default_postgres()

    from app.db.session import async_session_factory
    from app.db.user_datasource_db import get_active_datasource

    async with async_session_factory() as session:
        ds = await get_active_datasource(session, tenant_id)
        if ds is None:
            logger.debug(
                "Tenant %s has no datasource config, using default PostgreSQL", tenant_id
            )
            return _make_default_postgres()
        return _to_config_dict(ds)


async def resolve_datasource_by_id(datasource_id: int) -> dict | None:
    """Resolve a specific datasource by its ID.

    Returns a dict with keys: id, name, dsn, db_type.
    Returns None if not found.
    """
    from app.db.session import async_session_factory
    from app.db.models import UserDatasource
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(UserDatasource).where(UserDatasource.id == datasource_id)
        )
        ds = result.scalar_one_or_none()
        if ds is None:
            return None
        return _to_config_dict(ds)


def _to_config_dict(ds) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "dsn": ds.dsn,
        "db_type": ds.db_type,
    }
    logger.debug(
        "Resolved datasource for tenant %s: %s (%s)",
        tenant_id, ds.name, ds.db_type,
    )
    return {
        "id": ds.id,
        "name": ds.name,
        "dsn": ds.dsn,
        "db_type": ds.db_type,
    }


def _make_default_postgres() -> dict:
    import os
    return {
        "id": 0,
        "name": "Default PostgreSQL",
        "dsn": os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/dbname",
        ),
        "db_type": "postgres",
    }
