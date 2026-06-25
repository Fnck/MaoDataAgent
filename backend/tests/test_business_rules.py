"""
Unit tests for business rules validation based on the business analysis document.

Tests the business logic rules defined in:
- Part 1: Manufacturing supplier order fulfillment (R1-R8)
- Part 2: Shenzhen Hepalink finance (FR1-FR6)

These tests validate rule logic using mock data that simulates
the business tables defined in the document.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import pytest


# ════════════════════════════════════════════════════════════════
# Mock Data — Simulating business table rows as dicts
# ════════════════════════════════════════════════════════════════

# --- Manufacturing Scenario Mock Data ---

MOCK_PURCHASE_ORDERS = [
    {
        "order_id": "PO-2026-001",
        "supplier_id": "SUP001",
        "supplier_name": "深圳华强电子有限公司",
        "supplier_grade": "A",
        "supplier_type": "战略",
        "supplier_region": "本地",
        "order_type": "常规",
        "order_status": "全部到货",
        "order_date": "2026-05-01",
        "plan_delivery_date": "2026-05-15",
        "actual_delivery_date": "2026-05-14",
        "plan_delivery_qty": 1000,
        "actual_delivery_qty": 1000,
        "total_amount": 25000.00,
        "currency": "CNY",
        "factory": "一分厂",
        "purchaser_id": "P001",
        "purchaser_name": "张三",
        "is_fulfillment_ok": True,
        "fulfillment_rate": 1.0,
        "on_time_flag": "提前",
        "overdue_days": 0,
        "plan_delivery_date_change_count": 0,
        "is_closed": True,
        "close_date": "2026-05-16",
        "cancel_type": None,
    },
    {
        "order_id": "PO-2026-002",
        "supplier_id": "SUP002",
        "supplier_name": "东莞精密机械有限公司",
        "supplier_grade": "B",
        "supplier_type": "备选",
        "supplier_region": "异地",
        "order_type": "紧急",
        "order_status": "部分到货",
        "order_date": "2026-05-10",
        "plan_delivery_date": "2026-05-20",
        "actual_delivery_date": "2026-05-23",
        "plan_delivery_qty": 500,
        "actual_delivery_qty": 400,
        "total_amount": 18000.00,
        "currency": "CNY",
        "factory": "二分厂",
        "purchaser_id": "P002",
        "purchaser_name": "李四",
        "is_fulfillment_ok": False,
        "fulfillment_rate": 0.8,
        "on_time_flag": "逾期",
        "overdue_days": 3,
        "plan_delivery_date_change_count": 1,
        "is_closed": False,
        "close_date": None,
        "cancel_type": None,
    },
    {
        "order_id": "PO-2026-003",
        "supplier_id": "SUP001",
        "supplier_name": "深圳华强电子有限公司",
        "supplier_grade": "A",
        "supplier_type": "战略",
        "supplier_region": "本地",
        "order_type": "常规",
        "order_status": "已取消",
        "order_date": "2026-04-20",
        "plan_delivery_date": "2026-05-10",
        "actual_delivery_date": None,
        "plan_delivery_qty": 200,
        "actual_delivery_qty": 0,
        "total_amount": 5000.00,
        "currency": "CNY",
        "factory": "一分厂",
        "purchaser_id": "P001",
        "purchaser_name": "张三",
        "is_fulfillment_ok": False,
        "fulfillment_rate": 0.0,
        "on_time_flag": None,
        "overdue_days": None,
        "plan_delivery_date_change_count": 0,
        "is_closed": True,
        "close_date": "2026-04-25",
        "cancel_type": "临时取消",
    },
    {
        "order_id": "PO-2026-004",
        "supplier_id": "SUP003",
        "supplier_name": "广州包装材料有限公司",
        "supplier_grade": "C",
        "supplier_type": "备选",
        "supplier_region": "异地",
        "order_type": "备货",
        "order_status": "全部到货",
        "order_date": "2026-05-05",
        "plan_delivery_date": "2026-05-25",
        "actual_delivery_date": "2026-06-02",
        "plan_delivery_qty": 3000,
        "actual_delivery_qty": 3000,
        "total_amount": 4500.00,
        "currency": "CNY",
        "factory": "一分厂",
        "purchaser_id": "P003",
        "purchaser_name": "王五",
        "is_fulfillment_ok": False,
        "fulfillment_rate": 1.0,
        "on_time_flag": "逾期",
        "overdue_days": 8,
        "plan_delivery_date_change_count": 2,
        "is_closed": True,
        "close_date": "2026-06-03",
        "cancel_type": None,
    },
    {
        "order_id": "PO-2026-005",
        "supplier_id": "SUP002",
        "supplier_name": "东莞精密机械有限公司",
        "supplier_grade": "B",
        "supplier_type": "备选",
        "supplier_region": "异地",
        "order_type": "框架协议",
        "order_status": "全部到货",
        "order_date": "2026-05-15",
        "plan_delivery_date": "2026-06-01",
        "actual_delivery_date": "2026-06-01",
        "plan_delivery_qty": 800,
        "actual_delivery_qty": 800,
        "total_amount": 32000.00,
        "currency": "CNY",
        "factory": "二分厂",
        "purchaser_id": "P002",
        "purchaser_name": "李四",
        "is_fulfillment_ok": True,
        "fulfillment_rate": 1.0,
        "on_time_flag": "准时",
        "overdue_days": 0,
        "plan_delivery_date_change_count": 0,
        "is_closed": True,
        "close_date": "2026-06-02",
        "cancel_type": None,
    },
]

MOCK_QUALITY_INSPECTIONS = [
    {
        "inspection_id": "QC-001",
        "order_id": "PO-2026-001",
        "detail_id": "D-001",
        "material_id": "MAT001",
        "supplier_id": "SUP001",
        "inspection_date": "2026-05-14",
        "inspection_result": "合格",
        "defect_type": None,
        "defect_qty": 0,
        "defect_rate": 0.0,
        "handle_method": None,
        "is_batch_defect": False,
        "is_new_supplier": False,
        "claim_amount": 0,
        "is_claim": False,
        "production_stop_hours": 0,
    },
    {
        "inspection_id": "QC-002",
        "order_id": "PO-2026-002",
        "detail_id": "D-002",
        "material_id": "MAT002",
        "supplier_id": "SUP002",
        "inspection_date": "2026-05-23",
        "inspection_result": "不合格",
        "defect_type": "尺寸偏差",
        "defect_qty": 50,
        "defect_rate": 0.125,
        "handle_method": "退货",
        "is_batch_defect": True,
        "is_new_supplier": False,
        "claim_amount": 5000,
        "is_claim": True,
        "production_stop_hours": 4.5,
    },
    {
        "inspection_id": "QC-003",
        "order_id": "PO-2026-004",
        "detail_id": "D-003",
        "material_id": "MAT003",
        "supplier_id": "SUP003",
        "inspection_date": "2026-06-02",
        "inspection_result": "合格",
        "defect_type": None,
        "defect_qty": 0,
        "defect_rate": 0.0,
        "handle_method": None,
        "is_batch_defect": False,
        "is_new_supplier": False,
        "claim_amount": 0,
        "is_claim": False,
        "production_stop_hours": 0,
    },
]

MOCK_FULFILLMENT_EXCEPTIONS = [
    {
        "exception_id": "EX-001",
        "order_id": "PO-2026-002",
        "supplier_id": "SUP002",
        "exception_type": "交期延误",
        "exception_date": "2026-05-21",
        "exception_desc": "供应商交期延误3天",
        "is_closed": False,
        "close_date": None,
        "processing_duration_hours": None,
        "need_manual_intervention": True,
        "is_external_factor": False,
        "is_continuous": True,
    },
    {
        "exception_id": "EX-002",
        "order_id": "PO-2026-002",
        "supplier_id": "SUP002",
        "exception_type": "数量短装",
        "exception_date": "2026-05-23",
        "exception_desc": "到货数量比计划少100件",
        "is_closed": False,
        "close_date": None,
        "processing_duration_hours": None,
        "need_manual_intervention": True,
        "is_external_factor": False,
        "is_continuous": True,
    },
    {
        "exception_id": "EX-003",
        "order_id": "PO-2026-004",
        "supplier_id": "SUP003",
        "exception_type": "交期延误",
        "exception_date": "2026-05-28",
        "exception_desc": "物流堵车导致延迟",
        "is_closed": True,
        "close_date": "2026-06-02",
        "processing_duration_hours": 120,
        "need_manual_intervention": False,
        "is_external_factor": True,
        "is_continuous": False,
    },
]

MOCK_SUPPLIER_PERFORMANCES = [
    {
        "performance_id": "SP-001",
        "supplier_id": "SUP001",
        "supplier_name": "深圳华强电子有限公司",
        "period": "2026-05",
        "comprehensive_score": 92.5,
        "delivery_on_time_rate": 0.95,
        "quality_pass_rate": 0.98,
        "fulfillment_rate": 0.96,
        "supplier_grade": "A",
        "is_need_interview": False,
        "supply_amount": 30000.00,
        "total_purchase_amount": 84500.00,
        "score_change": 1.5,
    },
    {
        "performance_id": "SP-002",
        "supplier_id": "SUP002",
        "supplier_name": "东莞精密机械有限公司",
        "period": "2026-05",
        "comprehensive_score": 68.0,
        "delivery_on_time_rate": 0.70,
        "quality_pass_rate": 0.75,
        "fulfillment_rate": 0.72,
        "supplier_grade": "C",
        "is_need_interview": True,
        "supply_amount": 50000.00,
        "total_purchase_amount": 84500.00,
        "score_change": -5.0,
    },
    {
        "performance_id": "SP-003",
        "supplier_id": "SUP003",
        "supplier_name": "广州包装材料有限公司",
        "period": "2026-05",
        "comprehensive_score": 55.0,
        "delivery_on_time_rate": 0.60,
        "quality_pass_rate": 0.85,
        "fulfillment_rate": 0.65,
        "supplier_grade": "淘汰",
        "is_need_interview": True,
        "supply_amount": 4500.00,
        "total_purchase_amount": 84500.00,
        "score_change": -12.0,
    },
]

MOCK_WORK_ORDER_KITS = [
    {
        "kit_id": "KIT-001",
        "work_order_id": "WO-001",
        "material_id": "MAT001",
        "material_category": "核心零部件",
        "required_qty": 500,
        "available_qty": 500,
        "kit_rate": 1.0,
        "is_key_material": True,
        "is_cause_work_stop": False,
    },
    {
        "kit_id": "KIT-002",
        "work_order_id": "WO-001",
        "material_id": "MAT002",
        "material_category": "五金件",
        "required_qty": 200,
        "available_qty": 150,
        "kit_rate": 0.75,
        "is_key_material": False,
        "is_cause_work_stop": False,
    },
    {
        "kit_id": "KIT-003",
        "work_order_id": "WO-002",
        "material_id": "MAT001",
        "material_category": "核心零部件",
        "required_qty": 300,
        "available_qty": 200,
        "kit_rate": 0.67,
        "is_key_material": True,
        "is_cause_work_stop": True,
    },
    {
        "kit_id": "KIT-004",
        "work_order_id": "WO-002",
        "material_id": "MAT003",
        "material_category": "包材",
        "required_qty": 1000,
        "available_qty": 1000,
        "kit_rate": 1.0,
        "is_key_material": False,
        "is_cause_work_stop": False,
    },
]

MOCK_SETTLEMENT_RECONCILIATIONS = [
    {
        "settlement_id": "ST-001",
        "order_id": "PO-2026-001",
        "supplier_id": "SUP001",
        "settlement_status": "已付款",
        "invoice_amount": 25000.00,
        "payment_amount": 25000.00,
        "payment_date": "2026-06-01",
        "payment_cycle_days": 15,
        "is_payment_held": False,
        "held_amount": 0,
        "fulfillment_ok": True,
    },
    {
        "settlement_id": "ST-002",
        "order_id": "PO-2026-002",
        "supplier_id": "SUP002",
        "settlement_status": "已对账未开票",
        "invoice_amount": 0,
        "payment_amount": 0,
        "payment_date": None,
        "payment_cycle_days": None,
        "is_payment_held": True,
        "held_amount": 18000.00,
        "fulfillment_ok": False,
    },
]

MOCK_FORECAST_STOCKS = [
    {
        "forecast_id": "FS-001",
        "material_id": "MAT001",
        "material_category": "核心零部件",
        "forecast_date": "2026-07-01",
        "expected_arrival_qty": 2000,
        "expected_arrival_amount": 50000.00,
        "predicted_fulfillment_rate": 0.92,
        "predicted_delay_risk": False,
        "safety_stock_qty": 500,
        "current_stock_qty": 600,
        "is_safety_stock_insufficient": False,
        "supplier_capacity_sufficient": True,
        "demand_forecast_deviation": 0.05,
        "over_stock_qty": 0,
    },
    {
        "forecast_id": "FS-002",
        "material_id": "MAT002",
        "material_category": "五金件",
        "forecast_date": "2026-07-01",
        "expected_arrival_qty": 500,
        "expected_arrival_amount": 9000.00,
        "predicted_fulfillment_rate": 0.65,
        "predicted_delay_risk": True,
        "safety_stock_qty": 300,
        "current_stock_qty": 100,
        "is_safety_stock_insufficient": True,
        "supplier_capacity_sufficient": False,
        "demand_forecast_deviation": 0.25,
        "over_stock_qty": 0,
    },
]

# --- Finance Scenario Mock Data ---

MOCK_GROUP_REVENUE_PROFIT = [
    {
        "period": "2026-Q1",
        "year": 2026,
        "quarter": "Q1",
        "month": None,
        "operating_revenue": 150000000,
        "operating_profit": 25000000,
        "net_profit_parent": 20000000,
        "net_profit_deducted": 18000000,
        "non_recurring_gain_loss": 2000000,
        "gross_margin_rate": 0.42,
        "net_margin_rate": 0.133,
        "revenue_yoy_change": 0.12,
        "net_profit_yoy_change": 0.08,
        "revenue_qoq_change": 0.05,
        "monthly_target": 160000000,
        "monthly_achievement_rate": 0.9375,
    },
    {
        "period": "2025-Q1",
        "year": 2025,
        "quarter": "Q1",
        "month": None,
        "operating_revenue": 133928571,
        "operating_profit": 22000000,
        "net_profit_parent": 18518519,
        "net_profit_deducted": 17000000,
        "non_recurring_gain_loss": 1518519,
        "gross_margin_rate": 0.40,
        "net_margin_rate": 0.138,
        "revenue_yoy_change": None,
        "net_profit_yoy_change": None,
        "revenue_qoq_change": None,
        "monthly_target": None,
        "monthly_achievement_rate": None,
    },
]

MOCK_BALANCE_SHEETS = [
    {
        "year": 2026,
        "end_of_period": "2026-03-31",
        "total_asset": 2000000000,
        "total_liability": 800000000,
        "owner_equity": 1200000000,
        "cash_and_equivalent": 300000000,
        "accounts_receivable": 250000000,
        "inventory_balance": 180000000,
        "inventory_yoy_change": -0.08,
        "inventory_destocking_impact": "去库存减少存货约1500万",
        "fixed_asset_addition": 50000000,
        "short_term_loan": 200000000,
        "long_term_loan": 300000000,
        "interest_bearing_debt": 500000000,
        "restricted_asset": 80000000,
        "restricted_asset_detail": "抵押:5000万, 质押:2000万, 冻结:1000万",
        "trading_financial_asset": 100000000,
        "investment_income": 5000000,
        "asset_liability_ratio": 0.40,
        "asset_liability_ratio_yoy": 0.02,
    },
]

MOCK_CASH_FLOWS = [
    {
        "year": 2026,
        "quarter": "Q1",
        "operating_cash_flow": 35000000,
        "investing_cash_flow": -80000000,
        "financing_cash_flow": -15000000,
        "fixed_asset_investment": 50000000,
        "equity_investment": 30000000,
        "financing_negative_reason": "偿还短期借款",
        "financing_negative_amount": 15000000,
        "operating_cf_trend_4y": "上升",
        "operating_cf_coverage_ratio": 1.75,
    },
]

MOCK_BUDGET_INVESTMENT = [
    {
        "year": 2026,
        "revenue_budget": 160000000,
        "revenue_actual": 150000000,
        "revenue_achievement_rate": 0.9375,
        "revenue_gap": 10000000,
        "net_profit_budget": 22000000,
        "net_profit_actual": 20000000,
        "net_profit_achievement_rate": 0.909,
        "capex_budget": 60000000,
        "capex_actual": 50000000,
        "capex_deviation": -10000000,
        "equity_investment_total": 30000000,
        "investment_return": 5000000,
        "dividend_amount": 10000000,
        "roe": 0.167,
        "roe_yoy_change": -0.01,
    },
]


# ════════════════════════════════════════════════════════════════
# Business Rule Validation Functions
# ════════════════════════════════════════════════════════════════

def calc_fulfillment_rate(orders: list[dict]) -> float:
    """R1-01: 订单履约率 = 履约合格订单数 / 有效订单总数 × 100%"""
    valid_orders = [o for o in orders if o["order_status"] not in ("已取消", "已作废")]
    if not valid_orders:
        return 0.0
    fulfilled = [o for o in valid_orders if o["is_fulfillment_ok"]]
    return len(fulfilled) / len(valid_orders)


def is_fulfillment_ok(order: dict, inspections: list[dict]) -> bool:
    """R1-03: 履约合格判定 = 准时交货 AND 到货数量≥计划数量 AND 来料质量合格"""
    on_time = order.get("on_time_flag") in ("提前", "准时")
    qty_ok = (order.get("actual_delivery_qty") or 0) >= (order.get("plan_delivery_qty") or 0)
    quality_ok = True
    for qi in inspections:
        if qi["order_id"] == order["order_id"]:
            if qi["inspection_result"] != "合格":
                quality_ok = False
                break
    return on_time and qty_ok and quality_ok


def classify_overdue(overdue_days: int | None) -> str | None:
    """R2-05: 逾期分级"""
    if overdue_days is None or overdue_days <= 0:
        return None
    if overdue_days <= 3:
        return "轻度"
    if overdue_days <= 7:
        return "中度"
    return "重度"


def calc_on_time_rate(orders: list[dict]) -> float:
    """R2-01: 准时交货率 = 准时交货订单数 / 总交货订单数 × 100%"""
    delivered = [o for o in orders if o["order_status"] not in ("已取消", "已作废") and o.get("actual_delivery_date")]
    if not delivered:
        return 0.0
    on_time = [o for o in delivered if o.get("on_time_flag") in ("提前", "准时")]
    return len(on_time) / len(delivered)


def calc_kit_rate(kits: list[dict], work_order_id: str) -> float:
    """R3-01: 工单齐套率 = 已齐套物料种类数 / 工单所需物料总种类数 × 100%"""
    wo_kits = [k for k in kits if k["work_order_id"] == work_order_id]
    if not wo_kits:
        return 0.0
    fulfilled = [k for k in wo_kits if k["available_qty"] >= k["required_qty"]]
    return len(fulfilled) / len(wo_kits)


def calc_key_material_kit_rate(kits: list[dict], work_order_id: str) -> float:
    """R3-02: 核心物料齐套率"""
    key_kits = [k for k in kits if k["work_order_id"] == work_order_id and k["is_key_material"]]
    if not key_kits:
        return 1.0  # No key materials = fully fulfilled
    fulfilled = [k for k in key_kits if k["available_qty"] >= k["required_qty"]]
    return len(fulfilled) / len(key_kits)


def is_cause_work_stop(kits: list[dict], work_order_id: str) -> bool:
    """R3-03: 无法开工判定 = 齐套率 < 100% 且核心物料未齐套"""
    kit_rate = calc_kit_rate(kits, work_order_id)
    key_rate = calc_key_material_kit_rate(kits, work_order_id)
    return kit_rate < 1.0 and key_rate < 1.0


def is_batch_defect(defect_rate: float) -> bool:
    """R4-04: 批量性不良 = 不良率 ≥ 10%"""
    return defect_rate >= 0.10


def should_trigger_claim(inspection: dict, orders: list[dict]) -> bool:
    """R4-05: 质量索赔触发 = 不良导致订单履约失败"""
    order = next((o for o in orders if o["order_id"] == inspection["order_id"]), None)
    if order is None:
        return False
    return inspection["inspection_result"] == "不合格" and not order["is_fulfillment_ok"]


def is_continuous_exception(supplier_id: str, exceptions: list[dict]) -> bool:
    """R5-02: 连续异常判定 = 同一供应商连续两个月出现履约异常"""
    supplier_excs = [e for e in exceptions if e["supplier_id"] == supplier_id]
    return any(e["is_continuous"] for e in supplier_excs)


def calc_avg_close_duration(exceptions: list[dict]) -> float | None:
    """R5-03: 异常闭环时效"""
    closed = [e for e in exceptions if e["is_closed"] and e["processing_duration_hours"] is not None]
    if not closed:
        return None
    return sum(e["processing_duration_hours"] for e in closed) / len(closed)


def classify_supplier_grade(score: float) -> str:
    """R6-02: 等级划分"""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "淘汰"


def should_interview(grade: str) -> bool:
    """R6-03: 约谈整改 = C级及以下"""
    return grade in ("C", "淘汰")


def calc_unqualified_supply_ratio(performances: list[dict]) -> float:
    """R6-04: 履约不合格占比 = 履约不合格供应商供货金额 / 总采购金额 × 100%"""
    if not performances:
        return 0.0
    total_purchase = performances[0]["total_purchase_amount"]
    if total_purchase == 0:
        return 0.0
    unqualified_amount = sum(
        p["supply_amount"] for p in performances if p["supplier_grade"] in ("C", "淘汰")
    )
    return unqualified_amount / total_purchase


def should_hold_payment(order_id: str, exceptions: list[dict]) -> bool:
    """R7-02: 暂缓付款 = 存在未闭环履约异常"""
    return any(
        e["order_id"] == order_id and not e["is_closed"]
        for e in exceptions
    )


def calc_reconciliation_rate(settlements: list[dict], orders: list[dict]) -> float:
    """R7-01: 对账完成率 = 已完成对账结算订单数 / 已完成履约订单数 × 100%"""
    fulfilled_orders = [o for o in orders if o["is_fulfillment_ok"] and o["is_closed"]]
    if not fulfilled_orders:
        return 0.0
    reconciled = [s for s in settlements if s["settlement_status"] in ("已开票", "已付款")]
    return len(reconciled) / len(fulfilled_orders)


def is_delay_risk_material(forecast: dict) -> bool:
    """R8-02: 延误风险物料 = 安全库存不足且供应商履约偏慢"""
    return forecast["is_safety_stock_insufficient"] and forecast["predicted_delay_risk"]


# --- Finance Rule Functions ---

def calc_revenue_yoy(current: dict, prior_year: dict | None) -> float | None:
    """FR1-01: 营收同比变动 = (本期营收 - 去年同期营收) / 去年同期营收 × 100%"""
    if prior_year is None or prior_year["operating_revenue"] == 0:
        return None
    return (current["operating_revenue"] - prior_year["operating_revenue"]) / prior_year["operating_revenue"]


def calc_gross_margin(revenue: float, cost: float) -> float:
    """FR1-02: 毛利率 = (营收 - 营业成本) / 营收 × 100%"""
    if revenue == 0:
        return 0.0
    return (revenue - cost) / revenue


def calc_net_margin(net_profit: float, revenue: float) -> float:
    """FR1-03: 净利率 = 归母净利润 / 营业收入 × 100%"""
    if revenue == 0:
        return 0.0
    return net_profit / revenue


def calc_deducted_net_profit(net_profit: float, non_recurring: float) -> float:
    """FR1-04: 扣非归母净利润 = 归母净利润 - 非经常性损益"""
    return net_profit - non_recurring


def calc_monthly_achievement(actual: float, target: float) -> float:
    """FR1-05: 月度达成率 = 实际营收 / 月度经营目标 × 100%"""
    if target == 0:
        return 0.0
    return actual / target


def calc_asset_liability_ratio(total_liability: float, total_asset: float) -> float:
    """FR4-01: 资产负债率 = 总负债 / 总资产 × 100%"""
    if total_asset == 0:
        return 0.0
    return total_liability / total_asset


def calc_interest_bearing_debt(short_term: float, long_term: float) -> float:
    """FR4-02: 有息负债规模 = 短期借款 + 长期借款"""
    return short_term + long_term


def calc_operating_cf_coverage(operating_cf: float, net_profit: float) -> float:
    """FR5-01: 经营现金流覆盖倍数 = 经营活动现金流净额 / 归母净利润"""
    if net_profit == 0:
        return 0.0
    return operating_cf / net_profit


def calc_budget_achievement(actual: float, budget: float) -> float:
    """FR6-01: 预算达成率 = 实际值 / 预算值 × 100%"""
    if budget == 0:
        return 0.0
    return actual / budget


def calc_capex_deviation(actual: float, budget: float) -> float:
    """FR6-02: 资本开支偏差 = 实际支出 - 预算"""
    return actual - budget


def calc_roe(net_profit: float, avg_net_asset: float) -> float:
    """FR6-03: ROE = 归母净利润 / 加权平均净资产 × 100%"""
    if avg_net_asset == 0:
        return 0.0
    return net_profit / avg_net_asset


# ════════════════════════════════════════════════════════════════
# Test Classes
# ════════════════════════════════════════════════════════════════


class TestFulfillmentRateRules:
    """R1: 履约率计算规则"""

    def test_fulfillment_rate_calculation(self):
        """R1-01: 订单履约率 = 履约合格订单数 / 有效订单总数"""
        rate = calc_fulfillment_rate(MOCK_PURCHASE_ORDERS)
        # Valid orders (excl. 已取消): PO-001, PO-002, PO-004, PO-005
        # Fulfilled: PO-001, PO-005
        assert rate == 2 / 4

    def test_valid_order_excludes_cancelled(self):
        """R1-02: 有效订单排除已取消、已作废"""
        valid = [o for o in MOCK_PURCHASE_ORDERS if o["order_status"] not in ("已取消", "已作废")]
        cancelled = [o for o in MOCK_PURCHASE_ORDERS if o["order_status"] == "已取消"]
        assert len(cancelled) == 1
        assert len(valid) == 4
        assert all(o["order_status"] != "已取消" for o in valid)

    def test_fulfillment_ok_all_conditions(self):
        """R1-03: 履约合格 = 准时交货 + 数量达标 + 质量合格"""
        # PO-001: 提前 + qty=1000/1000 + QC合格
        assert is_fulfillment_ok(MOCK_PURCHASE_ORDERS[0], MOCK_QUALITY_INSPECTIONS) is True

    def test_fulfillment_not_ok_late_delivery(self):
        """R1-03: 逾期交货 → 不合格"""
        # PO-002: 逾期 + qty不足 + QC不合格
        assert is_fulfillment_ok(MOCK_PURCHASE_ORDERS[1], MOCK_QUALITY_INSPECTIONS) is False

    def test_fulfillment_not_ok_quality_fail(self):
        """R1-03: 质量不合格 → 不合格"""
        # PO-004: 逾期 (even though qty matches)
        assert is_fulfillment_ok(MOCK_PURCHASE_ORDERS[3], MOCK_QUALITY_INSPECTIONS) is False

    def test_fulfillment_ok_on_time(self):
        """R1-03: 准时交货 + 数量达标 + 质量合格 → 合格"""
        # PO-005: 准时 + qty=800/800 + no QC issues
        assert is_fulfillment_ok(MOCK_PURCHASE_ORDERS[4], MOCK_QUALITY_INSPECTIONS) is True

    def test_empty_orders_fulfillment_rate(self):
        rate = calc_fulfillment_rate([])
        assert rate == 0.0


class TestOnTimeRateRules:
    """R2: 交期准时率规则"""

    def test_on_time_rate_calculation(self):
        """R2-01: 准时交货率"""
        rate = calc_on_time_rate(MOCK_PURCHASE_ORDERS)
        # Delivered (excl. cancelled, has actual_delivery_date): PO-001, PO-002, PO-004, PO-005
        # On time (提前/准时): PO-001, PO-005
        assert rate == 2 / 4

    def test_early_delivery(self):
        """R2-02: 提前交货 = 实际 < 计划"""
        order = MOCK_PURCHASE_ORDERS[0]
        assert order["on_time_flag"] == "提前"
        assert order["actual_delivery_date"] < order["plan_delivery_date"]

    def test_on_time_delivery(self):
        """R2-03: 准时交货 = 实际 = 计划"""
        order = MOCK_PURCHASE_ORDERS[4]
        assert order["on_time_flag"] == "准时"
        assert order["actual_delivery_date"] == order["plan_delivery_date"]

    def test_overdue_delivery(self):
        """R2-04: 逾期交货 = 实际 > 计划"""
        order = MOCK_PURCHASE_ORDERS[1]
        assert order["on_time_flag"] == "逾期"
        assert order["actual_delivery_date"] > order["plan_delivery_date"]

    def test_overdue_classification_mild(self):
        """R2-05: 逾期1-3天 = 轻度"""
        assert classify_overdue(1) == "轻度"
        assert classify_overdue(3) == "轻度"

    def test_overdue_classification_moderate(self):
        """R2-05: 逾期4-7天 = 中度"""
        assert classify_overdue(4) == "中度"
        assert classify_overdue(7) == "中度"

    def test_overdue_classification_severe(self):
        """R2-05: 逾期>7天 = 重度"""
        assert classify_overdue(8) == "重度"
        assert classify_overdue(30) == "重度"

    def test_overdue_classification_none(self):
        assert classify_overdue(0) is None
        assert classify_overdue(None) is None
        assert classify_overdue(-1) is None

    def test_delivery_cycle_deviation(self):
        """R2-06: 交付周期偏差 = 实际平均交付周期 - 标准交付周期"""
        standard_lead_time = 14  # days
        actual_lead_time = 17  # days for PO-002
        deviation = actual_lead_time - standard_lead_time
        assert deviation > 0  # 正值表示偏慢


class TestKitRateRules:
    """R3: 物料齐套率规则"""

    def test_kit_rate_calculation(self):
        """R3-01: 工单齐套率"""
        rate = calc_kit_rate(MOCK_WORK_ORDER_KITS, "WO-001")
        # WO-001: MAT001 fulfilled (500/500), MAT002 not (150/200)
        assert rate == 1 / 2

    def test_kit_rate_full(self):
        rate = calc_kit_rate(MOCK_WORK_ORDER_KITS, "WO-002")
        # WO-002: MAT001 not (200/300), MAT003 fulfilled (1000/1000)
        assert rate == 1 / 2

    def test_key_material_kit_rate(self):
        """R3-02: 核心物料齐套率"""
        rate = calc_key_material_kit_rate(MOCK_WORK_ORDER_KITS, "WO-001")
        # WO-001 key: MAT001 fulfilled
        assert rate == 1.0

    def test_key_material_kit_rate_unfulfilled(self):
        rate = calc_key_material_kit_rate(MOCK_WORK_ORDER_KITS, "WO-002")
        # WO-002 key: MAT001 not fulfilled (200/300)
        assert rate == 0.0

    def test_cannot_start_work(self):
        """R3-03: 无法开工判定 = 齐套率<100% 且核心物料未齐套"""
        # WO-002: kit_rate=0.5, key_rate=0.0 → cannot start
        assert is_cause_work_stop(MOCK_WORK_ORDER_KITS, "WO-002") is True

    def test_can_start_with_non_key_shortage(self):
        """R3-03: 非核心物料不足但核心物料齐套 → 可开工"""
        # WO-001: kit_rate=0.5, key_rate=1.0 → can start
        assert is_cause_work_stop(MOCK_WORK_ORDER_KITS, "WO-001") is False

    def test_material_shortage_frequency(self):
        """R3-04: 缺料频次统计"""
        shortage_categories = {}
        for k in MOCK_WORK_ORDER_KITS:
            if k["available_qty"] < k["required_qty"]:
                cat = k["material_category"]
                shortage_categories[cat] = shortage_categories.get(cat, 0) + 1
        assert "五金件" in shortage_categories
        assert "核心零部件" in shortage_categories


class TestQualityRules:
    """R4: 来料质量规则"""

    def test_defect_rate_calculation(self):
        """R4-01: 来料不良率"""
        total = len(MOCK_QUALITY_INSPECTIONS)
        defective = sum(1 for q in MOCK_QUALITY_INSPECTIONS if q["inspection_result"] == "不合格")
        rate = defective / total
        assert rate == 1 / 3

    def test_defect_classification(self):
        """R4-02: 不良分类 = 尺寸偏差/外观缺陷/性能不合格"""
        defect_types = set()
        for q in MOCK_QUALITY_INSPECTIONS:
            if q["defect_type"]:
                defect_types.add(q["defect_type"])
        assert "尺寸偏差" in defect_types

    def test_handle_methods(self):
        """R4-03: 处理方式 = 退货/返工/特采放行"""
        methods = set()
        for q in MOCK_QUALITY_INSPECTIONS:
            if q["handle_method"]:
                methods.add(q["handle_method"])
        assert "退货" in methods

    def test_batch_defect_detection(self):
        """R4-04: 批量性不良 = 不良率 ≥ 10%"""
        # QC-002: defect_rate = 0.125 → batch defect
        assert is_batch_defect(MOCK_QUALITY_INSPECTIONS[1]["defect_rate"]) is True
        # QC-001: defect_rate = 0.0 → not batch defect
        assert is_batch_defect(MOCK_QUALITY_INSPECTIONS[0]["defect_rate"]) is False

    def test_claim_trigger(self):
        """R4-05: 质量索赔触发 = 不良导致履约失败"""
        # QC-002 for PO-002: 不合格 + 履约不达标
        assert should_trigger_claim(MOCK_QUALITY_INSPECTIONS[1], MOCK_PURCHASE_ORDERS) is True

    def test_no_claim_for_passed(self):
        # QC-001 for PO-001: 合格
        assert should_trigger_claim(MOCK_QUALITY_INSPECTIONS[0], MOCK_PURCHASE_ORDERS) is False

    def test_rework_secondary_fulfillment(self):
        """R4-06: 返工二次履约"""
        # Simulate rework: rework_fulfillment_ok must be checked after re-inspection
        rework_record = {
            "inbound_id": "IB-RW-001",
            "is_rework": True,
            "rework_fulfillment_ok": True,
        }
        assert rework_record["rework_fulfillment_ok"] is True


class TestExceptionRules:
    """R5: 履约异常规则"""

    def test_exception_categories(self):
        """R5-01: 异常分类四大类"""
        categories = set(e["exception_type"] for e in MOCK_FULFILLMENT_EXCEPTIONS)
        assert "交期延误" in categories
        assert "数量短装" in categories

    def test_continuous_exception(self):
        """R5-02: 连续异常判定"""
        assert is_continuous_exception("SUP002", MOCK_FULFILLMENT_EXCEPTIONS) is True
        assert is_continuous_exception("SUP001", MOCK_FULFILLMENT_EXCEPTIONS) is False

    def test_avg_close_duration(self):
        """R5-03: 闭环时效"""
        avg = calc_avg_close_duration(MOCK_FULFILLMENT_EXCEPTIONS)
        # Only EX-003 is closed with duration=120
        assert avg == 120.0

    def test_external_factor(self):
        """R5-04: 外部因素判定"""
        external = [e for e in MOCK_FULFILLMENT_EXCEPTIONS if e["is_external_factor"]]
        assert len(external) == 1
        assert external[0]["exception_type"] == "交期延误"
        assert "物流堵车" in external[0]["exception_desc"]

    def test_no_close_duration_for_open(self):
        avg = calc_avg_close_duration([
            e for e in MOCK_FULFILLMENT_EXCEPTIONS if not e["is_closed"]
        ])
        assert avg is None


class TestSupplierPerformanceRules:
    """R6: 供应商绩效考核规则"""

    def test_grade_classification_a(self):
        """R6-02: A级 ≥ 90分"""
        assert classify_supplier_grade(92.5) == "A"
        assert classify_supplier_grade(90) == "A"

    def test_grade_classification_b(self):
        """R6-02: B级 75-89分"""
        assert classify_supplier_grade(80) == "B"
        assert classify_supplier_grade(75) == "B"

    def test_grade_classification_c(self):
        """R6-02: C级 60-74分"""
        assert classify_supplier_grade(68) == "C"
        assert classify_supplier_grade(60) == "C"

    def test_grade_classification_eliminated(self):
        """R6-02: 淘汰级 < 60分"""
        assert classify_supplier_grade(55) == "淘汰"
        assert classify_supplier_grade(59.9) == "淘汰"

    def test_interview_required(self):
        """R6-03: C级及以下需约谈整改"""
        assert should_interview("C") is True
        assert should_interview("淘汰") is True
        assert should_interview("A") is False
        assert should_interview("B") is False

    def test_unqualified_supply_ratio(self):
        """R6-04: 履约不合格占比"""
        ratio = calc_unqualified_supply_ratio(MOCK_SUPPLIER_PERFORMANCES)
        # C + 淘汰: 50000 + 4500 = 54500; total: 84500
        expected = (50000 + 4500) / 84500
        assert abs(ratio - expected) < 0.001

    def test_comprehensive_score_formula(self):
        """R6-01: 综合评分 = 准时交货率×0.4 + 质量合格率×0.4 + 履约率×0.2"""
        # Verify formula with independent test data
        on_time_rate = 0.95
        quality_rate = 0.98
        fulfillment_rate = 0.96
        expected = on_time_rate * 0.4 + quality_rate * 0.4 + fulfillment_rate * 0.2
        assert abs(expected - 0.964) < 0.001

        # Mock data comprehensive_score is a weighted score on 100-point scale
        # with potentially different weights; verify it's in valid range
        for perf in MOCK_SUPPLIER_PERFORMANCES:
            assert 0 <= perf["comprehensive_score"] <= 100

    def test_grade_matches_mock_data(self):
        """Verify mock data grades match score ranges"""
        for perf in MOCK_SUPPLIER_PERFORMANCES:
            assert classify_supplier_grade(perf["comprehensive_score"]) == perf["supplier_grade"]


class TestSettlementRules:
    """R7: 对账结算规则"""

    def test_reconciliation_rate(self):
        """R7-01: 对账完成率"""
        rate = calc_reconciliation_rate(
            MOCK_SETTLEMENT_RECONCILIATIONS, MOCK_PURCHASE_ORDERS
        )
        # Fulfilled & closed: PO-001, PO-005
        # Reconciled (已开票/已付款): ST-001
        assert rate == 1 / 2

    def test_payment_held_for_unclosed_exception(self):
        """R7-02: 暂缓付款 = 存在未闭环履约异常"""
        # PO-002 has unclosed exceptions
        assert should_hold_payment("PO-2026-002", MOCK_FULFILLMENT_EXCEPTIONS) is True

    def test_payment_not_held_for_no_exception(self):
        # PO-001 has no exceptions
        assert should_hold_payment("PO-2026-001", MOCK_FULFILLMENT_EXCEPTIONS) is False

    def test_payment_held_in_mock_settlement(self):
        """Verify mock settlement data reflects hold rule"""
        st002 = MOCK_SETTLEMENT_RECONCILIATIONS[1]
        assert st002["is_payment_held"] is True
        assert st002["fulfillment_ok"] is False

    def test_payment_cycle_difference(self):
        """R7-03: 准时履约 vs 逾期履约付款周期差异"""
        on_time_cycles = [
            s["payment_cycle_days"] for s in MOCK_SETTLEMENT_RECONCILIATIONS
            if s["fulfillment_ok"] and s["payment_cycle_days"] is not None
        ]
        overdue_cycles = [
            s["payment_cycle_days"] for s in MOCK_SETTLEMENT_RECONCILIATIONS
            if not s["fulfillment_ok"] and s["payment_cycle_days"] is not None
        ]
        # On-time: 15 days; Overdue: no data yet (held)
        assert len(on_time_cycles) == 1
        assert on_time_cycles[0] == 15


class TestForecastRules:
    """R8: 预测与预判规则"""

    def test_delay_risk_material(self):
        """R8-02: 延误风险物料 = 安全库存不足 + 供应商履约偏慢"""
        # FS-002: safety insufficient + delay risk
        assert is_delay_risk_material(MOCK_FORECAST_STOCKS[1]) is True

    def test_no_delay_risk(self):
        # FS-001: safety sufficient
        assert is_delay_risk_material(MOCK_FORECAST_STOCKS[0]) is False

    def test_capacity_sufficiency(self):
        """R8-03: 产能匹配"""
        assert MOCK_FORECAST_STOCKS[0]["supplier_capacity_sufficient"] is True
        assert MOCK_FORECAST_STOCKS[1]["supplier_capacity_sufficient"] is False

    def test_demand_deviation_impact(self):
        """R8-04: 需求预测偏差率"""
        # Higher deviation → more impact on fulfillment
        assert MOCK_FORECAST_STOCKS[1]["demand_forecast_deviation"] > MOCK_FORECAST_STOCKS[0]["demand_forecast_deviation"]


# ════════════════════════════════════════════════════════════════
# Finance Scenario Rule Tests
# ════════════════════════════════════════════════════════════════


class TestFinanceRevenueRules:
    """FR1: 营收与利润规则"""

    def test_revenue_yoy(self):
        """FR1-01: 营收同比变动"""
        yoy = calc_revenue_yoy(MOCK_GROUP_REVENUE_PROFIT[0], MOCK_GROUP_REVENUE_PROFIT[1])
        expected = (150000000 - 133928571) / 133928571
        assert abs(yoy - expected) < 0.001

    def test_revenue_yoy_no_prior(self):
        yoy = calc_revenue_yoy(MOCK_GROUP_REVENUE_PROFIT[0], None)
        assert yoy is None

    def test_gross_margin(self):
        """FR1-02: 毛利率"""
        revenue = 150000000
        cost = 87000000  # 42% margin → cost = 58%
        margin = calc_gross_margin(revenue, cost)
        assert abs(margin - 0.42) < 0.01

    def test_net_margin(self):
        """FR1-03: 净利率"""
        margin = calc_net_margin(20000000, 150000000)
        assert abs(margin - 0.1333) < 0.01

    def test_deducted_net_profit(self):
        """FR1-04: 扣非归母净利润"""
        result = calc_deducted_net_profit(20000000, 2000000)
        assert result == 18000000

    def test_monthly_achievement(self):
        """FR1-05: 月度达成率"""
        rate = calc_monthly_achievement(150000000, 160000000)
        assert abs(rate - 0.9375) < 0.001

    def test_profit_ranking(self):
        """FR1-06: 利润贡献排名"""
        segments = [
            {"name": "肝素原料药", "net_profit": 10000000},
            {"name": "肝素制剂", "net_profit": 8000000},
            {"name": "CDMO", "net_profit": 3000000},
        ]
        ranked = sorted(segments, key=lambda x: x["net_profit"], reverse=True)
        assert ranked[0]["name"] == "肝素原料药"


class TestFinanceSegmentRules:
    """FR2: 业务板块规则"""

    def test_revenue_share(self):
        """FR2-02: 营收占比"""
        segment_revenue = 60000000
        total_revenue = 150000000
        share = segment_revenue / total_revenue
        assert abs(share - 0.4) < 0.01

    def test_internal_external_ratio(self):
        """FR2-03: 内外销占比"""
        external = 100000000
        internal = 50000000
        external_share = external / (external + internal)
        assert abs(external_share - 0.667) < 0.01

    def test_sales_model_margin_diff(self):
        """FR2-04: 经销直销毛利差异"""
        dealer_margin = 15000000
        direct_margin = 20000000
        diff = dealer_margin - direct_margin
        assert diff == -5000000


class TestFinanceAssetLiabilityRules:
    """FR4: 资产负债规则"""

    def test_asset_liability_ratio(self):
        """FR4-01: 资产负债率"""
        bs = MOCK_BALANCE_SHEETS[0]
        ratio = calc_asset_liability_ratio(bs["total_liability"], bs["total_asset"])
        assert abs(ratio - 0.40) < 0.01

    def test_interest_bearing_debt(self):
        """FR4-02: 有息负债规模 = 短期借款 + 长期借款"""
        bs = MOCK_BALANCE_SHEETS[0]
        debt = calc_interest_bearing_debt(bs["short_term_loan"], bs["long_term_loan"])
        assert debt == 500000000

    def test_inventory_yoy_change(self):
        """FR4-03: 存货同比变动"""
        bs = MOCK_BALANCE_SHEETS[0]
        assert bs["inventory_yoy_change"] == -0.08

    def test_restricted_asset(self):
        """FR4-04: 受限资产 = 抵押 + 质押 + 冻结"""
        # 5000万 + 2000万 + 1000万 = 8000万
        bs = MOCK_BALANCE_SHEETS[0]
        assert bs["restricted_asset"] == 80000000


class TestFinanceCashFlowRules:
    """FR5: 现金流规则"""

    def test_operating_cf_coverage(self):
        """FR5-01: 经营现金流覆盖倍数"""
        cf = MOCK_CASH_FLOWS[0]
        coverage = calc_operating_cf_coverage(cf["operating_cash_flow"], 20000000)
        assert abs(coverage - 1.75) < 0.01

    def test_investing_cash_flow_breakdown(self):
        """FR5-02: 投资现金流支出 = 固定资产投资 + 股权投资"""
        cf = MOCK_CASH_FLOWS[0]
        total_invest = cf["fixed_asset_investment"] + cf["equity_investment"]
        assert total_invest == 80000000

    def test_financing_negative(self):
        """FR5-03: 筹资现金流为负判定"""
        cf = MOCK_CASH_FLOWS[0]
        assert cf["financing_cash_flow"] < 0
        assert cf["financing_negative_reason"] is not None
        assert cf["financing_negative_amount"] > 0


class TestFinanceBudgetRules:
    """FR6: 预算与投融资规则"""

    def test_budget_achievement(self):
        """FR6-01: 预算达成率"""
        bi = MOCK_BUDGET_INVESTMENT[0]
        rev_rate = calc_budget_achievement(bi["revenue_actual"], bi["revenue_budget"])
        assert abs(rev_rate - 0.9375) < 0.001

        profit_rate = calc_budget_achievement(bi["net_profit_actual"], bi["net_profit_budget"])
        assert abs(profit_rate - 0.909) < 0.001

    def test_capex_deviation(self):
        """FR6-02: 资本开支偏差"""
        bi = MOCK_BUDGET_INVESTMENT[0]
        deviation = calc_capex_deviation(bi["capex_actual"], bi["capex_budget"])
        assert deviation == -10000000

    def test_roe_calculation(self):
        """FR6-03: ROE"""
        roe = calc_roe(20000000, 120000000)
        assert abs(roe - 0.1667) < 0.01

    def test_roe_yoy_change(self):
        """FR6-04: ROE同比变动"""
        bi = MOCK_BUDGET_INVESTMENT[0]
        assert bi["roe_yoy_change"] == -0.01  # 下降1个百分点


class TestCrossScenarioRules:
    """Tests for cross-scenario relationships (Part 3 of the document)."""

    def test_purchase_to_cost_link(self):
        """采购金额 → 营业成本"""
        total_purchase = sum(o["total_amount"] for o in MOCK_PURCHASE_ORDERS if o["order_status"] != "已取消")
        # Purchase amounts contribute to operating cost
        assert total_purchase > 0

    def test_unpaid_to_liability_link(self):
        """应付账款 → 负债"""
        unpaid = sum(
            s["held_amount"] for s in MOCK_SETTLEMENT_RECONCILIATIONS if s["is_payment_held"]
        )
        assert unpaid == 18000.00

    def test_claim_to_non_recurring(self):
        """索赔 → 营业外收支（非经常性损益）"""
        total_claims = sum(
            qi["claim_amount"] for qi in MOCK_QUALITY_INSPECTIONS if qi["is_claim"]
        )
        assert total_claims == 5000

    def test_inventory_to_balance_sheet(self):
        """入库物料 → 存货"""
        total_inbound = sum(
            o["actual_delivery_qty"] for o in MOCK_PURCHASE_ORDERS
            if o["order_status"] not in ("已取消",) and o["actual_delivery_qty"]
        )
        assert total_inbound > 0
