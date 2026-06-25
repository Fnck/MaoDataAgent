from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserDatasource


async def create_user_datasource(
    session: AsyncSession,
    tenant_id: int,
    name: str,
    dsn: str,
    db_type: str = "postgres",
    is_default: bool = False,
) -> int:
    """Create a new datasource config for a tenant and return its id."""
    ds = UserDatasource(
        tenant_id=tenant_id,
        name=name,
        dsn=dsn,
        db_type=db_type,
        is_active=False,
        is_default=is_default,
    )
    session.add(ds)
    await session.flush()
    return ds.id


async def list_user_datasources(
    session: AsyncSession, tenant_id: int
) -> list[UserDatasource]:
    """List all datasource configs for a tenant."""
    result = await session.execute(
        select(UserDatasource)
        .where(UserDatasource.tenant_id == tenant_id)
        .order_by(UserDatasource.id)
    )
    return list(result.scalars().all())


async def get_active_datasource(
    session: AsyncSession, tenant_id: int
) -> UserDatasource | None:
    """Get the currently active datasource for a tenant, falling back to default."""
    result = await session.execute(
        select(UserDatasource)
        .where(UserDatasource.tenant_id == tenant_id, UserDatasource.is_active == True)  # noqa: E712
    )
    ds = result.scalar_one_or_none()
    if ds is None:
        # Fallback to default
        result = await session.execute(
            select(UserDatasource)
            .where(UserDatasource.tenant_id == tenant_id, UserDatasource.is_default == True)  # noqa: E712
        )
        ds = result.scalar_one_or_none()
    return ds


async def update_user_datasource(
    session: AsyncSession,
    tenant_id: int,
    datasource_id: int,
    name: str | None = None,
    dsn: str | None = None,
    db_type: str | None = None,
) -> UserDatasource | None:
    """Update a datasource config. Returns updated object or None if not found."""
    row = await session.execute(
        select(UserDatasource).where(
            UserDatasource.id == datasource_id,
            UserDatasource.tenant_id == tenant_id,
        )
    )
    ds = row.scalar_one_or_none()
    if ds is None:
        return None
    if name is not None:
        ds.name = name
    if dsn is not None:
        ds.dsn = dsn
    if db_type is not None and not ds.is_default:
        ds.db_type = db_type
    await session.flush()
    return ds


async def activate_datasource(
    session: AsyncSession, tenant_id: int, datasource_id: int
) -> bool:
    """Set the given datasource as active, deactivating all others for the tenant."""
    row = await session.execute(
        select(UserDatasource).where(
            UserDatasource.id == datasource_id,
            UserDatasource.tenant_id == tenant_id,
        )
    )
    ds = row.scalar_one_or_none()
    if ds is None:
        return False

    await session.execute(
        update(UserDatasource)
        .where(UserDatasource.tenant_id == tenant_id)
        .values(is_active=False)
    )
    ds.is_active = True
    await session.flush()
    return True


async def delete_user_datasource(
    session: AsyncSession, tenant_id: int, datasource_id: int
) -> str | None:
    """Delete a datasource. Returns error message if not allowed, None on success."""
    row = await session.execute(
        select(UserDatasource).where(
            UserDatasource.id == datasource_id,
            UserDatasource.tenant_id == tenant_id,
        )
    )
    ds = row.scalar_one_or_none()
    if ds is None:
        return "Datasource not found"
    if ds.is_default:
        return "Cannot delete the default datasource"
    if ds.is_active:
        return "Cannot delete the active datasource — activate another first"
    await session.delete(ds)
    await session.flush()
    return None


async def ensure_default_datasource(
    session: AsyncSession, tenant_id: int
) -> None:
    """Ensure the tenant has at least a default PostgreSQL datasource."""
    result = await session.execute(
        select(UserDatasource).where(UserDatasource.tenant_id == tenant_id)
    )
    existing = result.scalars().all()
    if existing:
        return

    import os
    default_dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/dbname",
    )
    ds = UserDatasource(
        tenant_id=tenant_id,
        name="Default PostgreSQL",
        dsn=default_dsn,
        db_type="postgres",
        is_active=True,
        is_default=True,
    )
    session.add(ds)
    await session.flush()


async def init_default_datasources() -> None:
    """Ensure every user has a tenant and a default datasource.

    Handles all startup states:
    - Fresh deployment (no tenants, no datasources)
    - Migration ran (has Default tenant from migration)
    - Partial state (users exist but no tenant)
    """
    from app.db.session import async_session_factory
    from app.db.models import Tenant, TenantMember, User

    async with async_session_factory() as session:
        # 1. Ensure a "Default" tenant exists
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.name == "Default")
        )
        tenant = tenant_result.scalar_one_or_none()

        if tenant is None:
            # Check if ANY tenant exists (might be from migration with different name)
            all_tenants = await session.execute(select(Tenant))
            tenant = all_tenants.scalars().first()

        if tenant is None:
            tenant = Tenant(
                name="Default",
                description="Default tenant for localhost PostgreSQL",
                created_by_user_id=None,
            )
            session.add(tenant)
            await session.flush()

        # 2. Assign all users without a tenant to this one
        users_result = await session.execute(
            select(User).where(User.tenant_id == None)  # noqa: E711
        )
        unassigned_users = users_result.scalars().all()
        for user in unassigned_users:
            user.tenant_id = tenant.id
            # Add as member if not already
            existing_member = await session.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == tenant.id,
                    TenantMember.user_id == user.id,
                )
            )
            if existing_member.scalar_one_or_none() is None:
                role = "admin" if user.role == "admin" else "member"
                session.add(TenantMember(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role=role,
                ))

        # 3. Ensure default datasource for this tenant
        # Delete any stale datasource rows first (pointing to non-existent tenants)
        stale_check = await session.execute(select(Tenant))
        valid_tenant_ids = {t.id for t in stale_check.scalars().all()}
        all_ds = await session.execute(select(UserDatasource))
        for ds in all_ds.scalars().all():
            if ds.tenant_id not in valid_tenant_ids:
                await session.delete(ds)

        await ensure_default_datasource(session, tenant.id)
        await session.commit()
