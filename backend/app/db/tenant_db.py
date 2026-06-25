from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant, TenantMember, User


async def create_tenant(
    session: AsyncSession,
    name: str,
    description: str | None = None,
    created_by_user_id: int | None = None,
) -> Tenant:
    """Create a new tenant and return it."""
    tenant = Tenant(
        name=name,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    session.add(tenant)
    await session.flush()
    return tenant


async def get_tenant(session: AsyncSession, tenant_id: int) -> Tenant | None:
    """Get a tenant by ID."""
    result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_name(session: AsyncSession, name: str) -> Tenant | None:
    """Get a tenant by name."""
    result = await session.execute(
        select(Tenant).where(Tenant.name == name)
    )
    return result.scalar_one_or_none()


async def list_tenants(session: AsyncSession) -> list[Tenant]:
    """List all tenants."""
    result = await session.execute(
        select(Tenant).order_by(Tenant.id)
    )
    return list(result.scalars().all())


async def list_tenants_for_user(session: AsyncSession, user_id: int) -> list[Tenant]:
    """List tenants that a user is a member of."""
    result = await session.execute(
        select(Tenant)
        .join(TenantMember, TenantMember.tenant_id == Tenant.id)
        .where(TenantMember.user_id == user_id)
        .order_by(Tenant.id)
    )
    return list(result.scalars().all())


async def update_tenant(
    session: AsyncSession,
    tenant_id: int,
    name: str | None = None,
    description: str | None = None,
) -> Tenant | None:
    """Update a tenant's name or description."""
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        return None
    if name is not None:
        tenant.name = name
    if description is not None:
        tenant.description = description
    await session.flush()
    return tenant


async def delete_tenant(session: AsyncSession, tenant_id: int) -> bool:
    """Delete a tenant. Returns True if deleted, False if not found."""
    tenant = await get_tenant(session, tenant_id)
    if tenant is None:
        return False
    await session.delete(tenant)
    await session.flush()
    return True


# ── Tenant Members ──────────────────────────────────────

async def add_member(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    role: str = "member",
) -> TenantMember | None:
    """Add a user to a tenant. Returns None if already a member."""
    # Check if already a member
    existing = await session.execute(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None

    # Verify tenant and user exist
    tenant = await get_tenant(session, tenant_id)
    user = await session.execute(select(User).where(User.id == user_id))
    if tenant is None or user.scalar_one_or_none() is None:
        return None

    member = TenantMember(tenant_id=tenant_id, user_id=user_id, role=role)
    session.add(member)

    # Update user's tenant_id to this tenant
    await session.execute(
        update(User).where(User.id == user_id).values(tenant_id=tenant_id)
    )

    await session.flush()
    return member


async def remove_member(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> bool:
    """Remove a user from a tenant. Returns True if removed."""
    result = await session.execute(
        delete(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user_id,
        )
    )
    if result.rowcount == 0:
        return False

    # Clear user's tenant_id if this was their tenant
    await session.execute(
        update(User)
        .where(User.id == user_id, User.tenant_id == tenant_id)
        .values(tenant_id=None)
    )

    await session.flush()
    return True


async def list_members(session: AsyncSession, tenant_id: int) -> list[dict]:
    """List members of a tenant with user info."""
    result = await session.execute(
        select(TenantMember, User.username, User.role)
        .join(User, User.id == TenantMember.user_id)
        .where(TenantMember.tenant_id == tenant_id)
        .order_by(TenantMember.joined_at)
    )
    rows = result.all()
    return [
        {
            "id": row[0].id,
            "tenant_id": row[0].tenant_id,
            "user_id": row[0].user_id,
            "role": row[0].role,
            "username": row[1],
            "user_role": row[2],
            "joined_at": row[0].joined_at,
        }
        for row in rows
    ]
