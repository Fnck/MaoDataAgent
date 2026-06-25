from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_async_session
from app.ontology import service
from app.ontology.schemas import (
    ActivityCreate,
    ActivityMetricRelCreate,
    ActivityMetricRelOut,
    ActivityOut,
    ActivityEntityRelCreate,
    ActivityEntityRelOut,
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

router = APIRouter(prefix="/api/ontology", tags=["ontology"])


def _get_tenant_id(current_user: dict) -> int:
    """Extract tenant_id from current_user, raising if not assigned."""
    tenant_id = current_user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="User is not assigned to a tenant")
    return tenant_id


async def _resolve_datasource_name(datasource_id: int | None) -> str | None:
    """Resolve a datasource name from its ID. Returns None if not provided."""
    if datasource_id is None:
        return None
    from app.service.datasource_resolver import resolve_datasource_by_id
    ds = await resolve_datasource_by_id(datasource_id)
    return ds["name"] if ds else None


# ══════════════════════════════════════════════════════════
# Business Activities
# ══════════════════════════════════════════════════════════

@router.get("/activities", response_model=list[ActivityOut])
async def get_activities(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ActivityOut]:
    return await service.list_activities(session, _get_tenant_id(current_user))


@router.post("/activities", response_model=ActivityOut)
async def create_activity(
    body: ActivityCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ActivityOut:
    try:
        result = await service.create_activity(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/activities/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ActivityOut:
    try:
        result = await service.update_activity(session, activity_id, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_activity(session, activity_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Business Objects
# ══════════════════════════════════════════════════════════

@router.get("/objects", response_model=list[ObjectOut])
async def get_objects(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ObjectOut]:
    return await service.list_objects(session, _get_tenant_id(current_user))


@router.post("/objects", response_model=ObjectOut)
async def create_object(
    body: ObjectCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ObjectOut:
    try:
        result = await service.create_object(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/objects/{object_id}", response_model=ObjectOut)
async def update_object(
    object_id: int,
    body: ObjectUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ObjectOut:
    try:
        result = await service.update_object(session, object_id, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/objects/{object_id}")
async def delete_object(
    object_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_object(session, object_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Business Rules
# ══════════════════════════════════════════════════════════

@router.get("/rules", response_model=list[RuleOut])
async def get_rules(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[RuleOut]:
    return await service.list_rules(session, _get_tenant_id(current_user))


@router.post("/rules", response_model=RuleOut)
async def create_rule(
    body: RuleCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> RuleOut:
    try:
        result = await service.create_rule(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: int,
    body: RuleUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> RuleOut:
    try:
        result = await service.update_rule(session, rule_id, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_rule(session, rule_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Metrics
# ══════════════════════════════════════════════════════════

@router.get("/metrics", response_model=list[MetricOut])
async def get_metrics(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[MetricOut]:
    return await service.list_metrics(session, _get_tenant_id(current_user))


@router.post("/metrics", response_model=MetricOut)
async def create_metric(
    body: MetricCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MetricOut:
    try:
        result = await service.create_metric(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/metrics/{metric_id}", response_model=MetricOut)
async def update_metric(
    metric_id: int,
    body: MetricUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MetricOut:
    try:
        result = await service.update_metric(session, metric_id, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/metrics/{metric_id}")
async def delete_metric(
    metric_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_metric(session, metric_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Object Relationships
# ══════════════════════════════════════════════════════════

@router.get("/object-relationships", response_model=list[ObjectRelationshipOut])
async def get_object_relationships(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ObjectRelationshipOut]:
    return await service.list_object_relationships(session, _get_tenant_id(current_user))


@router.post("/object-relationships", response_model=ObjectRelationshipOut)
async def create_object_relationship(
    body: ObjectRelationshipCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ObjectRelationshipOut:
    try:
        result = await service.create_object_relationship(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/object-relationships/{relationship_id}")
async def delete_object_relationship(
    relationship_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_object_relationship(session, relationship_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Activity Metric Relations
# ══════════════════════════════════════════════════════════

@router.get("/activity-metric-rels", response_model=list[ActivityMetricRelOut])
async def get_activity_metric_rels(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ActivityMetricRelOut]:
    return await service.list_activity_metric_rels(session, _get_tenant_id(current_user))


@router.post("/activity-metric-rels", response_model=ActivityMetricRelOut)
async def create_activity_metric_rel(
    body: ActivityMetricRelCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ActivityMetricRelOut:
    try:
        result = await service.create_activity_metric_rel(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/activity-metric-rels/{rel_id}")
async def del_activity_metric_rel(
    rel_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_activity_metric_rel(session, rel_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Activity Entity Relations
# ══════════════════════════════════════════════════════════

@router.get("/activity-entity-rels", response_model=list[ActivityEntityRelOut])
async def get_activity_entity_rels(
    activity_id: int | None = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ActivityEntityRelOut]:
    return await service.list_activity_entity_rels(
        session, _get_tenant_id(current_user), activity_id,
    )


@router.post("/activity-entity-rels", response_model=ActivityEntityRelOut)
async def create_activity_entity_rel(
    body: ActivityEntityRelCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ActivityEntityRelOut:
    try:
        result = await service.create_activity_entity_rel(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/activity-entity-rels/{rel_id}")
async def del_activity_entity_rel(
    rel_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_activity_entity_rel(session, rel_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# Data Assets
# ══════════════════════════════════════════════════════════

@router.get("/data-assets", response_model=list[DataAssetOut])
async def get_data_assets(
    datasource_id: int | None = Query(None, description="Filter by datasource ID"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[DataAssetOut]:
    ds_name = await _resolve_datasource_name(datasource_id)
    return await service.list_data_assets(session, _get_tenant_id(current_user), ds_name)


@router.post("/data-assets", response_model=DataAssetOut)
async def create_data_asset(
    body: DataAssetCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DataAssetOut:
    try:
        result = await service.create_data_asset(session, body, _get_tenant_id(current_user))
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/data-assets/{asset_id}")
async def delete_data_asset(
    asset_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await service.delete_data_asset(session, asset_id, _get_tenant_id(current_user))
        await session.commit()
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
