from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ontology import database as db
from app.ontology.schemas import (
    ActivityCreate,
    ActivityEntityRelCreate,
    ActivityEntityRelOut,
    ActivityMetricRelCreate,
    ActivityMetricRelOut,
    ActivityOut,
    ActivityUpdate,
    DataAssetCreate,
    DataAssetOut,
    MetricCreate,
    MetricOut,
    MetricUpdate,
    ObjectCreate,
    ObjectOut,
    ObjectRelationshipCreate,
    ObjectRelationshipOut,
    ObjectUpdate,
    RuleCreate,
    RuleOut,
    RuleUpdate,
)


# ══════════════════════════════════════════════════════════
# Business Activity
# ══════════════════════════════════════════════════════════

async def list_activities(session: AsyncSession, tenant_id: int) -> list[ActivityOut]:
    rows = await db.list_activities(session, tenant_id)
    return [ActivityOut.model_validate(r) for r in rows]


async def get_activity(session: AsyncSession, activity_id: int, tenant_id: int) -> ActivityOut | None:
    row = await db.get_activity(session, activity_id, tenant_id)
    return ActivityOut.model_validate(row) if row else None


async def create_activity(session: AsyncSession, data: ActivityCreate, tenant_id: int) -> ActivityOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    act_id = await db.create_activity(session, **kwargs)
    row = await db.get_activity(session, act_id, tenant_id)
    return ActivityOut.model_validate(row)


async def update_activity(session: AsyncSession, activity_id: int, data: ActivityUpdate, tenant_id: int) -> ActivityOut:
    updated = await db.update_activity(session, activity_id, tenant_id, **data.model_dump(exclude_none=True))
    if not updated:
        raise ValueError("Activity not found")
    row = await db.get_activity(session, activity_id, tenant_id)
    return ActivityOut.model_validate(row)


async def delete_activity(session: AsyncSession, activity_id: int, tenant_id: int) -> None:
    ok = await db.delete_activity(session, activity_id, tenant_id)
    if not ok:
        raise ValueError("Activity not found")


# ══════════════════════════════════════════════════════════
# Business Object
# ══════════════════════════════════════════════════════════

async def list_objects(session: AsyncSession, tenant_id: int) -> list[ObjectOut]:
    rows = await db.list_objects(session, tenant_id)
    return [ObjectOut.model_validate(r) for r in rows]


async def get_object(session: AsyncSession, object_id: int, tenant_id: int) -> ObjectOut | None:
    row = await db.get_object(session, object_id, tenant_id)
    return ObjectOut.model_validate(row) if row else None


async def create_object(session: AsyncSession, data: ObjectCreate, tenant_id: int) -> ObjectOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    obj_id = await db.create_object(session, **kwargs)
    row = await db.get_object(session, obj_id, tenant_id)
    return ObjectOut.model_validate(row)


async def update_object(session: AsyncSession, object_id: int, data: ObjectUpdate, tenant_id: int) -> ObjectOut:
    updated = await db.update_object(session, object_id, tenant_id, **data.model_dump(exclude_none=True))
    if not updated:
        raise ValueError("Object not found")
    row = await db.get_object(session, object_id, tenant_id)
    return ObjectOut.model_validate(row)


async def delete_object(session: AsyncSession, object_id: int, tenant_id: int) -> None:
    ok = await db.delete_object(session, object_id, tenant_id)
    if not ok:
        raise ValueError("Object not found")


# ══════════════════════════════════════════════════════════
# Business Rule
# ══════════════════════════════════════════════════════════

async def list_rules(session: AsyncSession, tenant_id: int) -> list[RuleOut]:
    rows = await db.list_rules(session, tenant_id)
    return [RuleOut.model_validate(r) for r in rows]


async def get_rule(session: AsyncSession, rule_id: int, tenant_id: int) -> RuleOut | None:
    row = await db.get_rule(session, rule_id, tenant_id)
    return RuleOut.model_validate(row) if row else None


async def create_rule(session: AsyncSession, data: RuleCreate, tenant_id: int) -> RuleOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    rule_id = await db.create_rule(session, **kwargs)
    row = await db.get_rule(session, rule_id, tenant_id)
    return RuleOut.model_validate(row)


async def update_rule(session: AsyncSession, rule_id: int, data: RuleUpdate, tenant_id: int) -> RuleOut:
    updated = await db.update_rule(session, rule_id, tenant_id, **data.model_dump(exclude_none=True))
    if not updated:
        raise ValueError("Rule not found")
    row = await db.get_rule(session, rule_id, tenant_id)
    return RuleOut.model_validate(row)


async def delete_rule(session: AsyncSession, rule_id: int, tenant_id: int) -> None:
    ok = await db.delete_rule(session, rule_id, tenant_id)
    if not ok:
        raise ValueError("Rule not found")


# ══════════════════════════════════════════════════════════
# Metric
# ══════════════════════════════════════════════════════════

async def list_metrics(session: AsyncSession, tenant_id: int) -> list[MetricOut]:
    rows = await db.list_metrics(session, tenant_id)
    return [MetricOut.model_validate(r) for r in rows]


async def get_metric(session: AsyncSession, metric_id: int, tenant_id: int) -> MetricOut | None:
    row = await db.get_metric(session, metric_id, tenant_id)
    return MetricOut.model_validate(row) if row else None


async def create_metric(session: AsyncSession, data: MetricCreate, tenant_id: int) -> MetricOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    metric_id = await db.create_metric(session, **kwargs)
    row = await db.get_metric(session, metric_id, tenant_id)
    return MetricOut.model_validate(row)


async def update_metric(session: AsyncSession, metric_id: int, data: MetricUpdate, tenant_id: int) -> MetricOut:
    updated = await db.update_metric(session, metric_id, tenant_id, **data.model_dump(exclude_none=True))
    if not updated:
        raise ValueError("Metric not found")
    row = await db.get_metric(session, metric_id, tenant_id)
    return MetricOut.model_validate(row)


async def delete_metric(session: AsyncSession, metric_id: int, tenant_id: int) -> None:
    ok = await db.delete_metric(session, metric_id, tenant_id)
    if not ok:
        raise ValueError("Metric not found")


# ══════════════════════════════════════════════════════════
# Business Object Relationship
# ══════════════════════════════════════════════════════════

async def list_object_relationships(session: AsyncSession, tenant_id: int) -> list[ObjectRelationshipOut]:
    rows = await db.list_object_relationships(session, tenant_id)
    return [ObjectRelationshipOut.model_validate(r) for r in rows]


async def create_object_relationship(session: AsyncSession, data: ObjectRelationshipCreate, tenant_id: int) -> ObjectRelationshipOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    rel_id = await db.create_object_relationship(session, **kwargs)
    rows = await db.list_object_relationships(session, tenant_id)
    result = next((r for r in rows if r.relationship_id == rel_id), None)
    if result is None:
        raise ValueError("Failed to create relationship")
    return ObjectRelationshipOut.model_validate(result)


async def delete_object_relationship(session: AsyncSession, relationship_id: int, tenant_id: int) -> None:
    ok = await db.delete_object_relationship(session, relationship_id, tenant_id)
    if not ok:
        raise ValueError("Relationship not found")


# ══════════════════════════════════════════════════════════
# Activity Metric Relation
# ══════════════════════════════════════════════════════════

async def list_activity_metric_rels(session: AsyncSession, tenant_id: int) -> list[ActivityMetricRelOut]:
    rows = await db.list_metrics(session, tenant_id)
    # activity-metric relations are stored in activity_metric_rel table
    from sqlalchemy import select
    from app.ontology.models import ActivityMetricRelation
    result = await session.execute(
        select(ActivityMetricRelation)
        .where(ActivityMetricRelation.tenant_id == tenant_id)
        .order_by(ActivityMetricRelation.id)
    )
    rels = result.scalars().all()
    return [ActivityMetricRelOut.model_validate(r) for r in rels]


async def create_activity_metric_rel(session: AsyncSession, data: ActivityMetricRelCreate, tenant_id: int) -> ActivityMetricRelOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    rel_id = await db.create_activity_metric_rel(session, **kwargs)
    rows = await list_activity_metric_rels(session, tenant_id)
    result = next((r for r in rows if r.id == rel_id), None)
    if result is None:
        raise ValueError("Failed to create metric relation")
    return result


async def delete_activity_metric_rel(session: AsyncSession, rel_id: int, tenant_id: int) -> None:
    ok = await db.delete_activity_metric_rel(session, rel_id, tenant_id)
    if not ok:
        raise ValueError("Metric relation not found")


# ══════════════════════════════════════════════════════════
# Activity Entity Relation
# ══════════════════════════════════════════════════════════

async def list_activity_entity_rels(session: AsyncSession, tenant_id: int, activity_id: int | None = None) -> list[ActivityEntityRelOut]:
    rows = await db.list_activity_entity_rels(session, tenant_id, activity_id)
    return [ActivityEntityRelOut.model_validate(r) for r in rows]


async def create_activity_entity_rel(session: AsyncSession, data: ActivityEntityRelCreate, tenant_id: int) -> ActivityEntityRelOut:
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    rel_id = await db.create_activity_entity_rel(session, **kwargs)
    rows = await db.list_activity_entity_rels(session, tenant_id)
    result = next((r for r in rows if r.id == rel_id), None)
    if result is None:
        raise ValueError("Failed to create entity relation")
    return ActivityEntityRelOut.model_validate(result)


async def delete_activity_entity_rel(session: AsyncSession, rel_id: int, tenant_id: int) -> None:
    ok = await db.delete_activity_entity_rel(session, rel_id, tenant_id)
    if not ok:
        raise ValueError("Entity relation not found")


# ══════════════════════════════════════════════════════════
# Data Asset
# ══════════════════════════════════════════════════════════

async def list_data_assets(session: AsyncSession, tenant_id: int, datasource_name: str | None = None) -> list[DataAssetOut]:
    rows = await db.list_data_assets(session, tenant_id)
    if datasource_name:
        rows = [r for r in rows if r.datasource_name == datasource_name]
    return [DataAssetOut.model_validate(r) for r in rows]


async def get_data_asset(session: AsyncSession, asset_id: int, tenant_id: int) -> DataAssetOut | None:
    row = await db.get_data_asset(session, asset_id, tenant_id)
    return DataAssetOut.model_validate(row) if row else None


async def create_data_asset(session: AsyncSession, data: DataAssetCreate, tenant_id: int) -> DataAssetOut:
    existing = await db.get_data_asset_by_table(session, data.datasource_name, data.table_name, tenant_id)
    if existing:
        raise ValueError(f"Data asset already exists for {data.datasource_name}.{data.table_name}")
    kwargs = data.model_dump()
    kwargs["tenant_id"] = tenant_id
    asset_id = await db.create_data_asset(session, **kwargs)
    row = await db.get_data_asset(session, asset_id, tenant_id)
    return DataAssetOut.model_validate(row)


async def delete_data_asset(session: AsyncSession, asset_id: int, tenant_id: int) -> None:
    ok = await db.delete_data_asset(session, asset_id, tenant_id)
    if not ok:
        raise ValueError("Data asset not found")
