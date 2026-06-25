from __future__ import annotations

import logging
import re
from pathlib import Path

import aiosqlite
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import ColumnInfo, TableInfo
from app.service.datasource_resolver import resolve_active_datasource, resolve_datasource_by_id

logger = logging.getLogger(__name__)


def _validate_table_name(table_name: str) -> None:
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        raise ValueError(f"Invalid table name: {table_name}")


async def _resolve_ds(datasource_id: int | None = None) -> dict | None:
    """Resolve datasource: by ID if given, otherwise active for tenant."""
    if datasource_id is not None:
        return await resolve_datasource_by_id(datasource_id)
    return await resolve_active_datasource()


async def list_tables(datasource_id: int | None = None) -> list[TableInfo]:
    """List tables from the specified or active datasource. Returns empty on failure."""
    try:
        ds_config = await _resolve_ds(datasource_id)
    except Exception:
        return []
    if ds_config is None:
        return []

    ds_name = ds_config["name"]
    db_type = ds_config["db_type"]
    dsn = ds_config["dsn"]

    if db_type == "sqlite":
        return await _list_sqlite_tables_dsn(dsn, ds_name)
    elif db_type == "postgres":
        return await _list_postgres_tables_dsn(dsn, ds_name)
    else:
        logger.warning("Unsupported datasource type for listing: %s", db_type)
        return []


async def get_columns(datasource_id: int | None, table_name: str) -> list[ColumnInfo]:
    """Get column definitions for a table from the specified or active datasource."""
    try:
        ds_config = await _resolve_ds(datasource_id)
    except Exception:
        raise ValueError("Failed to resolve datasource")
    if ds_config is None:
        raise ValueError("No datasource configured")

    db_type = ds_config["db_type"]
    dsn = ds_config["dsn"]

    if db_type == "sqlite":
        return await _get_sqlite_columns_dsn(dsn, table_name)
    elif db_type == "postgres":
        return await _get_postgres_columns_dsn(dsn, table_name)
    else:
        raise ValueError(f"Unsupported datasource type: {db_type}")


# ── PostgreSQL helpers (user active datasource) ────────

async def _list_postgres_tables_dsn(dsn: str, ds_name: str) -> list[TableInfo]:
    """List tables from a PostgreSQL datasource identified by DSN.

    Returns empty list on connection failure instead of raising."""
    engine = create_async_engine(dsn, echo=False, connect_args={"timeout": 5})
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
            )
            rows = result.fetchall()
            return [TableInfo(datasource_name=ds_name, table_name=row[0]) for row in rows]
    except Exception as ex:
        logger.warning("Failed to list tables from %s: %s", ds_name, ex)
        return []
    finally:
        await engine.dispose()


async def _get_postgres_columns_dsn(dsn: str, table_name: str) -> list[ColumnInfo]:
    """Get columns for a table from a PostgreSQL datasource identified by DSN."""
    _validate_table_name(table_name)
    engine = create_async_engine(dsn, echo=False, connect_args={"timeout": 5})
    try:
        async with engine.connect() as conn:
            exists = await conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :tbl)"
                ),
                {"tbl": table_name},
            )
            if not exists.scalar():
                raise ValueError(f"Table not found: {table_name}")

            result = await conn.execute(
                text(
                    "SELECT column_name, data_type, "
                    "COALESCE(pg_catalog.col_description(format('%I.%I', table_schema, table_name)::regclass::oid, ordinal_position), '') AS col_comment "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :tbl "
                    "ORDER BY ordinal_position"
                ),
                {"tbl": table_name},
            )
            rows = result.fetchall()
            return [
                ColumnInfo(name=row[0], type=row[1], comment=row[2] or None)
                for row in rows
            ]
    finally:
        await engine.dispose()


# ── SQLite helpers (user active datasource) ────────────

async def _list_sqlite_tables_dsn(dsn: str, ds_name: str) -> list[TableInfo]:
    """List tables from a SQLite datasource identified by DSN (file path)."""
    path = dsn
    db_path = Path(path)
    if not db_path.exists():
        logger.warning("SQLite database file not found: %s", path)
        return []

    async with aiosqlite.connect(path) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [TableInfo(datasource_name=ds_name, table_name=row[0]) for row in rows]


async def _get_sqlite_columns_dsn(dsn: str, table_name: str) -> list[ColumnInfo]:
    """Get columns for a table from a SQLite datasource identified by DSN (file path)."""
    _validate_table_name(table_name)
    path = dsn
    db_path = Path(path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {path}")

    async with aiosqlite.connect(path) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ) as cursor:
            if await cursor.fetchone() is None:
                raise ValueError(f"Table not found: {table_name}")

        async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
            rows = await cursor.fetchall()
            return [
                ColumnInfo(name=row[1], type=row[2], comment=None)
                for row in rows
            ]
