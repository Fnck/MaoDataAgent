from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.auth import get_current_user
from app.db.session import get_async_session
from app.db.user_datasource_db import (
    activate_datasource,
    create_user_datasource,
    delete_user_datasource,
    list_user_datasources,
    update_user_datasource,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/datasources", tags=["user-datasources"])


def _get_tenant_id(current_user: dict) -> int:
    tenant_id = current_user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="User is not assigned to a tenant")
    return tenant_id


class CreateDatasourceRequest(BaseModel):
    name: str
    dsn: str
    db_type: str = "postgres"


class UpdateDatasourceRequest(BaseModel):
    name: str | None = None
    dsn: str | None = None
    db_type: str | None = None


class TestConnectionRequest(BaseModel):
    dsn: str
    db_type: str = "postgres"


class DatasourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    dsn: str
    db_type: str
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            # asyncpg returns '+00' instead of '+00:00'
            v = v.replace("+00", "+00:00")
            return datetime.fromisoformat(v)
        return v


@router.get("", response_model=list[DatasourceResponse])
async def list_datasources(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    sources = await list_user_datasources(session, _get_tenant_id(current_user))
    return [DatasourceResponse.model_validate(s) for s in sources]


@router.post("", response_model=DatasourceResponse)
async def create_datasource(
    body: CreateDatasourceRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = _get_tenant_id(current_user)
    ds_id = await create_user_datasource(
        session,
        tenant_id=tenant_id,
        name=body.name,
        dsn=body.dsn,
        db_type=body.db_type,
    )
    await session.commit()
    sources = await list_user_datasources(session, tenant_id)
    result = next((s for s in sources if s.id == ds_id), None)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create datasource")
    return DatasourceResponse.model_validate(result)


@router.put("/{datasource_id}/activate")
async def set_active_datasource(
    datasource_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    ok = await activate_datasource(session, _get_tenant_id(current_user), datasource_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Datasource not found")
    await session.commit()
    return {"status": "ok", "active_datasource_id": datasource_id}


@router.put("/{datasource_id}", response_model=DatasourceResponse)
async def edit_datasource(
    datasource_id: int,
    body: UpdateDatasourceRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    ds = await update_user_datasource(
        session,
        tenant_id=_get_tenant_id(current_user),
        datasource_id=datasource_id,
        name=body.name,
        dsn=body.dsn,
        db_type=body.db_type,
    )
    if ds is None:
        raise HTTPException(status_code=404, detail="Datasource not found")
    await session.commit()
    return DatasourceResponse.model_validate(ds)


@router.post("/test")
async def test_connection(
    body: TestConnectionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Test if the given DSN can connect successfully."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(body.dsn, echo=False)
        async with engine.connect() as conn:
            await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=10.0,
            )
            await conn.commit()
        await engine.dispose()
        return {"status": "ok"}
    except asyncio.TimeoutError:
        logger.warning("Connection test timed out for DSN: %s", body.dsn)
        return {"status": "error", "detail": "Connection timed out after 10 seconds"}
    except Exception as e:
        logger.warning("Connection test failed for DSN %s: %s", body.dsn, e)
        return {"status": "error", "detail": str(e)}


@router.delete("/{datasource_id}")
async def remove_datasource(
    datasource_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    error = await delete_user_datasource(session, _get_tenant_id(current_user), datasource_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    await session.commit()
    return {"status": "deleted"}
