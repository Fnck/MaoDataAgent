from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.db.session import get_async_session
from app.db.tenant_db import (
    add_member,
    create_tenant,
    delete_tenant,
    get_tenant,
    list_members,
    list_tenants,
    list_tenants_for_user,
    remove_member,
    update_tenant,
)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# ── Schemas ─────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    description: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_by_user_id: int | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            v = v.replace("+00", "+00:00")
            return datetime.fromisoformat(v)
        return v


class AddMemberRequest(BaseModel):
    user_id: int
    role: str = "member"


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    user_id: int
    username: str
    user_role: str
    role: str
    joined_at: datetime

    @field_validator("joined_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            v = v.replace("+00", "+00:00")
            return datetime.fromisoformat(v)
        return v


# ── Tenant CRUD ─────────────────────────────────────────

@router.post("", response_model=TenantResponse)
async def api_create_tenant(
    body: TenantCreate,
    current_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new tenant (admin only)."""
    tenant = await create_tenant(
        session,
        name=body.name,
        description=body.description,
        created_by_user_id=current_user["id"],
    )
    await session.commit()
    return TenantResponse.model_validate(tenant)


@router.get("", response_model=list[TenantResponse])
async def api_list_tenants(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List tenants. Admins see all; regular users see only their own."""
    if current_user.get("role") == "admin":
        return [TenantResponse.model_validate(t) for t in await list_tenants(session)]
    else:
        return [
            TenantResponse.model_validate(t)
            for t in await list_tenants_for_user(session, current_user["id"])
        ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def api_get_tenant(
    tenant_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a tenant by ID."""
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def api_update_tenant(
    tenant_id: int,
    body: TenantUpdate,
    current_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a tenant (admin only)."""
    tenant = await update_tenant(
        session,
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
    )
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await session.commit()
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}")
async def api_delete_tenant(
    tenant_id: int,
    current_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a tenant (admin only)."""
    ok = await delete_tenant(session, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await session.commit()
    return {"status": "deleted"}


# ── Tenant Members ──────────────────────────────────────

@router.get("/{tenant_id}/members", response_model=list[MemberResponse])
async def api_list_members(
    tenant_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List members of a tenant."""
    members = await list_members(session, tenant_id)
    return [MemberResponse(**m) for m in members]


@router.post("/{tenant_id}/members", response_model=MemberResponse)
async def api_add_member(
    tenant_id: int,
    body: AddMemberRequest,
    current_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Add a user to a tenant (admin only)."""
    member = await add_member(
        session,
        tenant_id=tenant_id,
        user_id=body.user_id,
        role=body.role,
    )
    if member is None:
        raise HTTPException(status_code=400, detail="Cannot add member (user may already be a member or not found)")
    await session.commit()
    # Reload with user info
    members = await list_members(session, tenant_id)
    result = next((m for m in members if m["user_id"] == body.user_id), None)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to reload member")
    return MemberResponse(**result)


@router.delete("/{tenant_id}/members/{user_id}")
async def api_remove_member(
    tenant_id: int,
    user_id: int,
    current_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove a user from a tenant (admin only)."""
    ok = await remove_member(session, tenant_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    await session.commit()
    return {"status": "removed"}
