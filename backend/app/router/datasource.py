from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.models import ColumnInfo, TableInfo
from app.service.datasource import get_columns, list_tables
from app.service.datasource_resolver import set_current_tenant_id

router = APIRouter(prefix="/api/datasource", tags=["datasource"])


@router.get("/tables", response_model=list[TableInfo])
async def datasource_tables(
    datasource_id: int | None = Query(None, description="Specific datasource ID; omit to use active"),
    current_user: dict = Depends(get_current_user),
) -> list[TableInfo]:
    set_current_tenant_id(current_user.get("tenant_id"))
    try:
        return await list_tables(datasource_id)
    except ValueError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.get("/table/{table_name}/columns", response_model=list[ColumnInfo])
async def datasource_columns(
    table_name: str,
    datasource_id: int | None = Query(None, description="Specific datasource ID; omit to use active"),
    current_user: dict = Depends(get_current_user),
) -> list[ColumnInfo]:
    set_current_tenant_id(current_user.get("tenant_id"))
    try:
        return await get_columns(datasource_id, table_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
