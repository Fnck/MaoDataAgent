from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ══════════════════════════════════════════════════════════
# Business Activity
# ══════════════════════════════════════════════════════════

class ActivityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pre_activities: Optional[str] = None
    post_activities: Optional[str] = None
    operated_objects: Optional[str] = None
    input_entities: Optional[str] = None
    output_entities: Optional[str] = None
    node_metrics: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pre_activities: Optional[str] = None
    post_activities: Optional[str] = None
    operated_objects: Optional[str] = None
    input_entities: Optional[str] = None
    output_entities: Optional[str] = None
    node_metrics: Optional[str] = None
    updated_by: Optional[str] = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    pre_activities: Optional[str] = None
    post_activities: Optional[str] = None
    operated_objects: Optional[str] = None
    input_entities: Optional[str] = None
    output_entities: Optional[str] = None
    node_metrics: Optional[str] = None
    created_by: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Business Object
# ══════════════════════════════════════════════════════════

class ObjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    related_entities: Optional[str] = None
    entity_relationships: Optional[str] = None
    maintainer: Optional[str] = None
    department: Optional[str] = None
    permissions: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class ObjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    related_entities: Optional[str] = None
    entity_relationships: Optional[str] = None
    maintainer: Optional[str] = None
    department: Optional[str] = None
    permissions: Optional[str] = None
    updated_by: Optional[str] = None


class ObjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    object_id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    related_entities: Optional[str] = None
    entity_relationships: Optional[str] = None
    maintainer: Optional[str] = None
    department: Optional[str] = None
    permissions: Optional[str] = None
    created_by: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Business Rule
# ══════════════════════════════════════════════════════════

class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    condition_expression: Optional[str] = None
    associated_activity_id: Optional[int] = None
    associated_object_id: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    condition_expression: Optional[str] = None
    associated_activity_id: Optional[int] = None
    associated_object_id: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    updated_by: Optional[str] = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    condition_expression: Optional[str] = None
    associated_activity_id: Optional[int] = None
    associated_object_id: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Metric
# ══════════════════════════════════════════════════════════

class MetricCreate(BaseModel):
    name: str
    business_meaning: Optional[str] = None
    calculation_formula: Optional[str] = None
    query_logic: Optional[str] = None
    unit: Optional[str] = None
    data_source: Optional[str] = None
    refresh_cycle: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class MetricUpdate(BaseModel):
    name: Optional[str] = None
    business_meaning: Optional[str] = None
    calculation_formula: Optional[str] = None
    query_logic: Optional[str] = None
    unit: Optional[str] = None
    data_source: Optional[str] = None
    refresh_cycle: Optional[str] = None
    updated_by: Optional[str] = None


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_id: int
    tenant_id: int
    name: str
    business_meaning: Optional[str] = None
    calculation_formula: Optional[str] = None
    query_logic: Optional[str] = None
    unit: Optional[str] = None
    data_source: Optional[str] = None
    refresh_cycle: Optional[str] = None
    created_by: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Business Object Relationship
# ══════════════════════════════════════════════════════════

class ObjectRelationshipCreate(BaseModel):
    object_id_1: int
    object_id_2: int
    relationship_type: Optional[str] = None
    join_logic: Optional[str] = None
    constraint_logic: Optional[str] = None
    join_direction: Optional[str] = None
    union_logic: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class ObjectRelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    relationship_id: int
    tenant_id: int
    object_id_1: int
    object_id_2: int
    relationship_type: Optional[str] = None
    join_logic: Optional[str] = None
    constraint_logic: Optional[str] = None
    join_direction: Optional[str] = None
    union_logic: Optional[str] = None
    created_by: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Activity Metric Relation
# ══════════════════════════════════════════════════════════

class ActivityMetricRelCreate(BaseModel):
    activity_id: int
    metric_id: int
    usage_stage: Optional[str] = None


class ActivityMetricRelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    activity_id: int
    metric_id: int
    usage_stage: Optional[str] = None
    created_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Activity Entity Relation
# ══════════════════════════════════════════════════════════

class ActivityEntityRelCreate(BaseModel):
    activity_id: int
    entity_name: str
    entity_type: Optional[str] = None  # INPUT / OUTPUT
    order_index: Optional[int] = None


class ActivityEntityRelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    activity_id: int
    entity_name: str
    entity_type: Optional[str] = None
    order_index: Optional[int] = None
    created_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════
# Data Asset
# ══════════════════════════════════════════════════════════

class DataAssetCreate(BaseModel):
    datasource_name: str
    table_name: str
    table_comment: Optional[str] = None


class DataAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    datasource_name: str
    table_name: str
    table_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
