"""
Business domain ORM models for manufacturing supplier order fulfillment scenario.

These models represent the 10 core business tables defined in:
《智能问数业务分析-数据表与流程规则梳理》

Registered with Base so they are created by Base.metadata.create_all().
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PurchaseOrderModel(Base):
    __tablename__ = "purchase_order"

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_grade: Mapped[str] = mapped_column(String(10), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_region: Mapped[str] = mapped_column(String(20), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    order_status: Mapped[str] = mapped_column(String(20), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    plan_delivery_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    actual_delivery_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="CNY")
    factory: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    purchaser_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    purchaser_name: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_fulfillment_ok: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    fulfillment_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    on_time_flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    overdue_days: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    plan_delivery_date_change_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    is_closed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cancel_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OrderMaterialDetailModel(Base):
    __tablename__ = "order_material_detail"

    detail_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    material_id: Mapped[str] = mapped_column(String(20), nullable=False)
    material_name: Mapped[str] = mapped_column(String(80), nullable=False)
    material_category: Mapped[str] = mapped_column(String(30), nullable=False)
    is_key_material: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    plan_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    actual_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    gap_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    standard_lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_delivery_count: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    is_inspection_exempt: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    inspection_type: Mapped[Optional[str]] = mapped_column(String(10), default="全检")


class InboundRecordModel(Base):
    __tablename__ = "inbound_record"

    inbound_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    detail_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    material_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    inbound_type: Mapped[str] = mapped_column(String(30), nullable=False)
    inbound_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    inbound_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    inbound_date: Mapped[date] = mapped_column(Date, nullable=False)
    inbound_time_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    warehouse_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    plan_inbound_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    is_rework: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    rework_fulfillment_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class QualityInspectionModel(Base):
    __tablename__ = "quality_inspection"

    inspection_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    detail_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    material_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    inspection_result: Mapped[str] = mapped_column(String(10), nullable=False)
    defect_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    defect_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    defect_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), default=0)
    handle_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_batch_defect: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_new_supplier: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    claim_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    is_claim: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    production_stop_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), default=0)


class FulfillmentExceptionModel(Base):
    __tablename__ = "fulfillment_exception"

    exception_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    exception_type: Mapped[str] = mapped_column(String(30), nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_desc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_closed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    processing_duration_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    need_manual_intervention: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    is_external_factor: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_continuous: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)


class LogisticsReceiptModel(Base):
    __tablename__ = "logistics_receipt"

    receipt_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    logistics_type: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_region: Mapped[str] = mapped_column(String(20), nullable=False)
    plan_arrival_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_arrival_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_delayed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    delay_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), default=0)
    unload_overtime: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    inspection_overtime: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_return_exchange: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)


class SettlementReconciliationModel(Base):
    __tablename__ = "settlement_reconciliation"

    settlement_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    settlement_status: Mapped[str] = mapped_column(String(20), nullable=False)
    invoice_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    payment_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_cycle_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_payment_held: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    held_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    fulfillment_ok: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)


class SupplierPerformanceModel(Base):
    __tablename__ = "supplier_performance"

    performance_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    comprehensive_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    delivery_on_time_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    quality_pass_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    fulfillment_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    supplier_grade: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_need_interview: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    supply_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    total_purchase_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    score_change: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)


class WorkOrderKitModel(Base):
    __tablename__ = "work_order_kit"

    kit_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    material_id: Mapped[str] = mapped_column(String(20), nullable=False)
    material_category: Mapped[str] = mapped_column(String(30), nullable=False)
    required_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    available_qty: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    kit_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    is_key_material: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_cause_work_stop: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)


class ForecastStockModel(Base):
    __tablename__ = "forecast_stock"

    forecast_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    material_id: Mapped[str] = mapped_column(String(20), nullable=False)
    material_category: Mapped[str] = mapped_column(String(30), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_arrival_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    expected_arrival_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), default=0)
    predicted_fulfillment_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    predicted_delay_risk: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    safety_stock_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    current_stock_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
    is_safety_stock_insufficient: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    supplier_capacity_sufficient: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    demand_forecast_deviation: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    over_stock_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), default=0)
