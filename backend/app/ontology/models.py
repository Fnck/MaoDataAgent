from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ── Business Activity ──────────────────────────────────

class BusinessActivity(Base):
    __tablename__ = "business_activity"

    activity_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pre_activities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    post_activities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operated_objects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    node_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


# ── Business Object ────────────────────────────────────

class BusinessObject(Base):
    __tablename__ = "business_object"

    object_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_relationships: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    maintainer: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


# ── Business Rule ──────────────────────────────────────

class BusinessRule(Base):
    __tablename__ = "business_rule"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    condition_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    associated_activity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    associated_object_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


# ── Metric ─────────────────────────────────────────────

class Metric(Base):
    __tablename__ = "metric"

    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_meaning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calculation_formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    refresh_cycle: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


# ── Business Object Relationship ───────────────────────

class BusinessObjectRelationship(Base):
    __tablename__ = "business_object_relationship"

    relationship_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    object_id_1: Mapped[int] = mapped_column(Integer, nullable=False)
    object_id_2: Mapped[int] = mapped_column(Integer, nullable=False)
    relationship_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    join_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraint_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    join_direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    union_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())


# ── Activity Metric Relation ───────────────────────────

class ActivityMetricRelation(Base):
    __tablename__ = "activity_metric_rel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())


# ── Activity Entity Relation ───────────────────────────

class ActivityEntityRelation(Base):
    __tablename__ = "activity_entity_rel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # INPUT / OUTPUT
    order_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())


# ── Data Asset (Managed Table List) ────────────────────

class DataAsset(Base):
    __tablename__ = "data_asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    datasource_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    table_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())
