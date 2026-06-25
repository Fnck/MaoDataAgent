from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.ontology.models import (
    ActivityEntityRelation,
    ActivityMetricRelation,
    BusinessActivity,
    BusinessObject,
    BusinessObjectRelationship,
    BusinessRule,
    DataAsset,
    Metric,
)
from app.db.session import engine


# ── Table Initialization ───────────────────────────────

async def init_ontology_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ══════════════════════════════════════════════════════════
# Business Activity CRUD
# ══════════════════════════════════════════════════════════

async def list_activities(session: AsyncSession, tenant_id: int) -> list[BusinessActivity]:
    stmt = (
        select(BusinessActivity)
        .where(BusinessActivity.tenant_id == tenant_id)
        .order_by(BusinessActivity.created_time.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_activity(session: AsyncSession, activity_id: int, tenant_id: int) -> BusinessActivity | None:
    stmt = select(BusinessActivity).where(
        BusinessActivity.activity_id == activity_id,
        BusinessActivity.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_activity(session: AsyncSession, **kwargs) -> int:
    activity = BusinessActivity(**kwargs)
    session.add(activity)
    await session.flush()
    return activity.activity_id


async def update_activity(session: AsyncSession, activity_id: int, tenant_id: int, **kwargs) -> bool:
    stmt = select(BusinessActivity).where(
        BusinessActivity.activity_id == activity_id,
        BusinessActivity.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    activity = result.scalar_one_or_none()
    if not activity:
        return False
    for key, value in kwargs.items():
        if hasattr(activity, key):
            setattr(activity, key, value)
    return True


async def delete_activity(session: AsyncSession, activity_id: int, tenant_id: int) -> bool:
    # Delete related join records first
    await session.execute(
        delete(ActivityMetricRelation).where(
            ActivityMetricRelation.activity_id == activity_id,
            ActivityMetricRelation.tenant_id == tenant_id,
        )
    )
    await session.execute(
        delete(ActivityEntityRelation).where(
            ActivityEntityRelation.activity_id == activity_id,
            ActivityEntityRelation.tenant_id == tenant_id,
        )
    )
    stmt = delete(BusinessActivity).where(
        BusinessActivity.activity_id == activity_id,
        BusinessActivity.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Business Object CRUD
# ══════════════════════════════════════════════════════════

async def list_objects(session: AsyncSession, tenant_id: int) -> list[BusinessObject]:
    stmt = (
        select(BusinessObject)
        .where(BusinessObject.tenant_id == tenant_id)
        .order_by(BusinessObject.created_time.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_object(session: AsyncSession, object_id: int, tenant_id: int) -> BusinessObject | None:
    stmt = select(BusinessObject).where(
        BusinessObject.object_id == object_id,
        BusinessObject.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_object(session: AsyncSession, **kwargs) -> int:
    obj = BusinessObject(**kwargs)
    session.add(obj)
    await session.flush()
    return obj.object_id


async def update_object(session: AsyncSession, object_id: int, tenant_id: int, **kwargs) -> bool:
    stmt = select(BusinessObject).where(
        BusinessObject.object_id == object_id,
        BusinessObject.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        return False
    for key, value in kwargs.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    return True


async def delete_object(session: AsyncSession, object_id: int, tenant_id: int) -> bool:
    stmt = delete(BusinessObject).where(
        BusinessObject.object_id == object_id,
        BusinessObject.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Business Rule CRUD
# ══════════════════════════════════════════════════════════

async def list_rules(session: AsyncSession, tenant_id: int) -> list[BusinessRule]:
    stmt = (
        select(BusinessRule)
        .where(BusinessRule.tenant_id == tenant_id)
        .order_by(BusinessRule.created_time.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_rule(session: AsyncSession, rule_id: int, tenant_id: int) -> BusinessRule | None:
    stmt = select(BusinessRule).where(
        BusinessRule.rule_id == rule_id,
        BusinessRule.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_rule(session: AsyncSession, **kwargs) -> int:
    rule = BusinessRule(**kwargs)
    session.add(rule)
    await session.flush()
    return rule.rule_id


async def update_rule(session: AsyncSession, rule_id: int, tenant_id: int, **kwargs) -> bool:
    stmt = select(BusinessRule).where(
        BusinessRule.rule_id == rule_id,
        BusinessRule.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        return False
    for key, value in kwargs.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    return True


async def delete_rule(session: AsyncSession, rule_id: int, tenant_id: int) -> bool:
    stmt = delete(BusinessRule).where(
        BusinessRule.rule_id == rule_id,
        BusinessRule.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Metric CRUD
# ══════════════════════════════════════════════════════════

async def list_metrics(session: AsyncSession, tenant_id: int) -> list[Metric]:
    stmt = (
        select(Metric)
        .where(Metric.tenant_id == tenant_id)
        .order_by(Metric.created_time.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_metric(session: AsyncSession, metric_id: int, tenant_id: int) -> Metric | None:
    stmt = select(Metric).where(
        Metric.metric_id == metric_id,
        Metric.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_metric(session: AsyncSession, **kwargs) -> int:
    metric = Metric(**kwargs)
    session.add(metric)
    await session.flush()
    return metric.metric_id


async def update_metric(session: AsyncSession, metric_id: int, tenant_id: int, **kwargs) -> bool:
    stmt = select(Metric).where(
        Metric.metric_id == metric_id,
        Metric.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    metric = result.scalar_one_or_none()
    if not metric:
        return False
    for key, value in kwargs.items():
        if hasattr(metric, key):
            setattr(metric, key, value)
    return True


async def delete_metric(session: AsyncSession, metric_id: int, tenant_id: int) -> bool:
    # Delete related join records
    await session.execute(
        delete(ActivityMetricRelation).where(
            ActivityMetricRelation.metric_id == metric_id,
            ActivityMetricRelation.tenant_id == tenant_id,
        )
    )
    stmt = delete(Metric).where(
        Metric.metric_id == metric_id,
        Metric.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Business Object Relationship CRUD
# ══════════════════════════════════════════════════════════

async def list_object_relationships(session: AsyncSession, tenant_id: int) -> list[BusinessObjectRelationship]:
    stmt = (
        select(BusinessObjectRelationship)
        .where(BusinessObjectRelationship.tenant_id == tenant_id)
        .order_by(BusinessObjectRelationship.created_time.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_object_relationship(session: AsyncSession, **kwargs) -> int:
    rel = BusinessObjectRelationship(**kwargs)
    session.add(rel)
    await session.flush()
    return rel.relationship_id


async def delete_object_relationship(session: AsyncSession, relationship_id: int, tenant_id: int) -> bool:
    stmt = delete(BusinessObjectRelationship).where(
        BusinessObjectRelationship.relationship_id == relationship_id,
        BusinessObjectRelationship.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Data Asset CRUD
# ══════════════════════════════════════════════════════════

async def list_data_assets(session: AsyncSession, tenant_id: int) -> list[DataAsset]:
    stmt = (
        select(DataAsset)
        .where(DataAsset.tenant_id == tenant_id)
        .order_by(DataAsset.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_data_asset(session: AsyncSession, asset_id: int, tenant_id: int) -> DataAsset | None:
    stmt = select(DataAsset).where(
        DataAsset.id == asset_id,
        DataAsset.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_data_asset_by_table(session: AsyncSession, datasource_name: str, table_name: str, tenant_id: int) -> DataAsset | None:
    stmt = select(DataAsset).where(
        DataAsset.datasource_name == datasource_name,
        DataAsset.table_name == table_name,
        DataAsset.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_data_asset(session: AsyncSession, **kwargs) -> int:
    asset = DataAsset(**kwargs)
    session.add(asset)
    await session.flush()
    return asset.id


async def delete_data_asset(session: AsyncSession, asset_id: int, tenant_id: int) -> bool:
    stmt = delete(DataAsset).where(
        DataAsset.id == asset_id,
        DataAsset.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Activity Metric Relation CRUD
# ══════════════════════════════════════════════════════════

async def create_activity_metric_rel(session: AsyncSession, **kwargs) -> int:
    rel = ActivityMetricRelation(**kwargs)
    session.add(rel)
    await session.flush()
    return rel.id


async def delete_activity_metric_rel(session: AsyncSession, rel_id: int, tenant_id: int) -> bool:
    stmt = delete(ActivityMetricRelation).where(
        ActivityMetricRelation.id == rel_id,
        ActivityMetricRelation.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


# ══════════════════════════════════════════════════════════
# Activity Entity Relation CRUD
# ══════════════════════════════════════════════════════════

async def list_activity_entity_rels(
    session: AsyncSession,
    tenant_id: int,
    activity_id: int | None = None,
) -> list[ActivityEntityRelation]:
    stmt = select(ActivityEntityRelation).where(
        ActivityEntityRelation.tenant_id == tenant_id,
    )
    if activity_id is not None:
        stmt = stmt.where(ActivityEntityRelation.activity_id == activity_id)
    result = await session.execute(stmt.order_by(ActivityEntityRelation.order_index))
    return list(result.scalars().all())


async def create_activity_entity_rel(session: AsyncSession, **kwargs) -> int:
    rel = ActivityEntityRelation(**kwargs)
    session.add(rel)
    await session.flush()
    return rel.id


async def delete_activity_entity_rel(session: AsyncSession, rel_id: int, tenant_id: int) -> bool:
    stmt = delete(ActivityEntityRelation).where(
        ActivityEntityRelation.id == rel_id,
        ActivityEntityRelation.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0
