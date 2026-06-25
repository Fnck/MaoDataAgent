"""
Unit tests for Ontology API endpoints (/api/ontology).

Includes mock data based on the business analysis document:
- Part 1: Manufacturing supplier order fulfillment scenario
- Part 2: Shenzhen Hepalink finance scenario

Tests cover CRUD operations for:
- Business Activities (业务活动)
- Business Objects (业务对象)
- Business Rules (业务规则)
- Metrics (指标)
- Object Relationships (对象关系)
- Activity-Metric Relations (活动-指标关系)
- Activity-Entity Relations (活动-实体关系)
- Data Assets (数据资产)
"""
from __future__ import annotations

import json

import pytest
from httpx import AsyncClient


# ════════════════════════════════════════════════════════════════
# Mock Data — Manufacturing Supplier Order Fulfillment Scenario
# ════════════════════════════════════════════════════════════════

MANUFACTURING_BUSINESS_OBJECTS = [
    {
        "name": "采购订单主表",
        "description": "记录采购订单的核心信息，包括供应商、订单状态、交货日期、履约率等",
        "related_entities": json.dumps([
            {"table": "purchase_order", "role": "header"},
        ], ensure_ascii=False),
        "entity_relationships": json.dumps({
            "purchase_order": {"1:N": "order_material_detail"},
        }, ensure_ascii=False),
        "maintainer": "采购部",
        "department": "采购部",
    },
    {
        "name": "订单物料明细表",
        "description": "采购订单的物料明细，记录物料品类、计划/实际数量、交付周期等",
        "related_entities": json.dumps([
            {"table": "order_material_detail", "role": "detail"},
        ], ensure_ascii=False),
        "entity_relationships": json.dumps({
            "order_material_detail": {"N:1": "purchase_order"},
        }, ensure_ascii=False),
        "department": "采购部",
    },
    {
        "name": "入库记录表",
        "description": "记录物料入库信息，包括入库类型、数量、金额、返工标记等",
        "related_entities": json.dumps([
            {"table": "inbound_record", "role": "header"},
        ], ensure_ascii=False),
        "department": "仓储部",
    },
    {
        "name": "来料质量检验表",
        "description": "记录来料质量检验结果，包括不良类型、不良率、处理方式、索赔等",
        "related_entities": json.dumps([
            {"table": "quality_inspection", "role": "header"},
        ], ensure_ascii=False),
        "department": "质检部",
    },
    {
        "name": "履约异常表",
        "description": "记录履约过程中的异常信息，包括交期延误、数量短装、质量不良等",
        "related_entities": json.dumps([
            {"table": "fulfillment_exception", "role": "header"},
        ], ensure_ascii=False),
        "department": "采购部",
    },
    {
        "name": "物流到货签收表",
        "description": "记录物流签收信息，包括物流方式、延迟情况、卸货超时等",
        "related_entities": json.dumps([
            {"table": "logistics_receipt", "role": "header"},
        ], ensure_ascii=False),
        "department": "物流部",
    },
    {
        "name": "对账结算表",
        "description": "记录对账结算信息，包括结算状态、付款金额、暂缓付款等",
        "related_entities": json.dumps([
            {"table": "settlement_reconciliation", "role": "header"},
        ], ensure_ascii=False),
        "department": "财务部",
    },
    {
        "name": "供应商绩效考核表",
        "description": "记录供应商绩效考核数据，包括综合评分、准时交货率、质量合格率等",
        "related_entities": json.dumps([
            {"table": "supplier_performance", "role": "header"},
        ], ensure_ascii=False),
        "department": "采购部",
    },
    {
        "name": "生产工单物料齐套表",
        "description": "记录生产工单物料齐套情况，包括齐套率、核心物料标记等",
        "related_entities": json.dumps([
            {"table": "work_order_kit", "role": "header"},
        ], ensure_ascii=False),
        "department": "生产部",
    },
    {
        "name": "备货预测表",
        "description": "记录备货预测数据，包括预计到货、预测履约率、安全库存等",
        "related_entities": json.dumps([
            {"table": "forecast_stock", "role": "header"},
        ], ensure_ascii=False),
        "department": "采购部",
    },
]

MANUFACTURING_BUSINESS_ACTIVITIES = [
    {
        "name": "采购需求下达",
        "description": "采购部门根据生产计划下达采购订单",
        "pre_activities": None,
        "post_activities": "供应商确认接单",
        "operated_objects": None,
        "input_entities": json.dumps(["生产计划"], ensure_ascii=False),
        "output_entities": json.dumps(["purchase_order"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["订单数量", "订单金额"]}, ensure_ascii=False),
    },
    {
        "name": "供应商确认接单",
        "description": "供应商确认订单并反馈交期",
        "pre_activities": "采购需求下达",
        "post_activities": "订单交期确认/变更",
        "input_entities": json.dumps(["purchase_order"], ensure_ascii=False),
        "output_entities": json.dumps(["purchase_order"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["接单响应率"]}, ensure_ascii=False),
    },
    {
        "name": "订单交期确认/变更",
        "description": "确认计划交货日期，或因需求变化变更交期",
        "pre_activities": "供应商确认接单",
        "post_activities": "供应商备货生产",
        "input_entities": json.dumps(["purchase_order"], ensure_ascii=False),
        "output_entities": json.dumps(["purchase_order"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["交期变更次数"]}, ensure_ascii=False),
    },
    {
        "name": "到货签收",
        "description": "货物到达仓库，签收确认",
        "pre_activities": "在途跟踪",
        "post_activities": "卸货入库",
        "input_entities": json.dumps(["logistics_receipt"], ensure_ascii=False),
        "output_entities": json.dumps(["logistics_receipt"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["延迟到货率", "卸货超时率"]}, ensure_ascii=False),
    },
    {
        "name": "来料质量检验",
        "description": "IQC对来料进行质量检验",
        "pre_activities": "卸货入库",
        "post_activities": "合格入库/不合格处理",
        "input_entities": json.dumps(["inbound_record"], ensure_ascii=False),
        "output_entities": json.dumps(["quality_inspection"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["不良率", "批量性不良率"]}, ensure_ascii=False),
    },
    {
        "name": "物料齐套检查",
        "description": "检查生产工单所需物料是否齐套",
        "pre_activities": "合格入库/不合格处理",
        "post_activities": "对账开票",
        "input_entities": json.dumps(["work_order_kit"], ensure_ascii=False),
        "output_entities": json.dumps(["work_order_kit"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["齐套率", "核心物料齐套率"]}, ensure_ascii=False),
    },
    {
        "name": "履约异常识别",
        "description": "识别交期延误、短装、质量不良等异常",
        "pre_activities": None,
        "post_activities": "异常处理闭环",
        "input_entities": json.dumps(["fulfillment_exception"], ensure_ascii=False),
        "output_entities": json.dumps(["fulfillment_exception"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["异常率", "闭环时效"]}, ensure_ascii=False),
    },
    {
        "name": "供应商绩效考核",
        "description": "定期对供应商进行履约评分和分级",
        "pre_activities": None,
        "post_activities": None,
        "input_entities": json.dumps(["supplier_performance"], ensure_ascii=False),
        "output_entities": json.dumps(["supplier_performance"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["综合评分", "等级"]}, ensure_ascii=False),
    },
    {
        "name": "对账开票",
        "description": "采购与供应商对账并开具发票",
        "pre_activities": "物料齐套检查",
        "post_activities": "付款结算",
        "input_entities": json.dumps(["settlement_reconciliation"], ensure_ascii=False),
        "output_entities": json.dumps(["settlement_reconciliation"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["对账完成率"]}, ensure_ascii=False),
    },
    {
        "name": "付款结算",
        "description": "按合同约定付款",
        "pre_activities": "对账开票",
        "post_activities": None,
        "input_entities": json.dumps(["settlement_reconciliation"], ensure_ascii=False),
        "output_entities": json.dumps(["settlement_reconciliation"], ensure_ascii=False),
        "node_metrics": json.dumps({"key_metrics": ["付款周期", "暂缓付款率"]}, ensure_ascii=False),
    },
]

# Business Rules from the document (R1-R8 for manufacturing, FR1-FR6 for finance)
MANUFACTURING_BUSINESS_RULES = [
    {
        "name": "订单履约率计算",
        "description": "履约合格订单数 / 有效订单总数 × 100%",
        "category": "履约率规则",
        "condition_expression": "is_fulfillment_ok == True AND order_status NOT IN ('已取消', '已作废')",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "履约合格判定",
        "description": "同时满足：①准时交货 ②到货数量≥计划数量 ③来料质量合格",
        "category": "履约率规则",
        "condition_expression": "on_time_flag IN ('提前','准时') AND actual_delivery_qty >= plan_delivery_qty AND quality_inspection.inspection_result == '合格'",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "逾期分级",
        "description": "逾期1-3天（轻度）、逾期3-7天（中度）、逾期7天以上（重度）",
        "category": "交期准时率规则",
        "condition_expression": "overdue_days BETWEEN 1 AND 3 -> 轻度; BETWEEN 4 AND 7 -> 中度; > 7 -> 重度",
        "priority": 2,
        "status": "active",
    },
    {
        "name": "批量性不良判定",
        "description": "同一供应商同一物料同一批次不良率 ≥ 10%",
        "category": "来料质量规则",
        "condition_expression": "defect_rate >= 0.10",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "供应商等级划分",
        "description": "A级（≥90分）、B级（75-89分）、C级（60-74分）、淘汰级（<60分）",
        "category": "供应商绩效考核规则",
        "condition_expression": "comprehensive_score >= 90 -> A; >= 75 -> B; >= 60 -> C; < 60 -> 淘汰",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "暂缓付款触发",
        "description": "存在未闭环履约异常 → 暂缓付款",
        "category": "对账结算规则",
        "condition_expression": "EXISTS fulfillment_exception WHERE is_closed == False",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "连续异常判定",
        "description": "同一供应商连续两个月出现履约异常",
        "category": "履约异常规则",
        "condition_expression": "is_continuous == True",
        "priority": 2,
        "status": "active",
    },
    {
        "name": "无法开工判定",
        "description": "工单齐套率 < 100% 且核心物料未齐套 → 标记为无法开工",
        "category": "物料齐套率规则",
        "condition_expression": "kit_rate < 1.0 AND is_key_material == True AND available_qty < required_qty",
        "priority": 1,
        "status": "active",
    },
]

# Metrics from the document
MANUFACTURING_METRICS = [
    {
        "name": "订单履约率",
        "business_meaning": "衡量供应商按时按质按量交付订单的能力",
        "calculation_formula": "履约合格订单数 / 有效订单总数 × 100%",
        "query_logic": "SELECT COUNT(*) FROM purchase_order WHERE is_fulfillment_ok = 1 AND order_status NOT IN ('已取消') / COUNT(*) * 100",
        "unit": "%",
        "data_source": "purchase_order",
        "refresh_cycle": "月",
    },
    {
        "name": "准时交货率",
        "business_meaning": "衡量供应商按时交货的比例",
        "calculation_formula": "准时交货订单数 / 总交货订单数 × 100%",
        "query_logic": "SELECT COUNT(*) FROM purchase_order WHERE on_time_flag IN ('提前','准时') / COUNT(*) * 100",
        "unit": "%",
        "data_source": "purchase_order",
        "refresh_cycle": "月",
    },
    {
        "name": "来料不良率",
        "business_meaning": "衡量来料质量水平",
        "calculation_formula": "不良批次数 / 总检验批次数 × 100%",
        "query_logic": "SELECT COUNT(*) FROM quality_inspection WHERE inspection_result = '不合格' / COUNT(*) * 100",
        "unit": "%",
        "data_source": "quality_inspection",
        "refresh_cycle": "月",
    },
    {
        "name": "工单齐套率",
        "business_meaning": "衡量生产工单物料齐套程度",
        "calculation_formula": "已齐套物料种类数 / 工单所需物料总种类数 × 100%",
        "query_logic": "SELECT SUM(CASE WHEN available_qty >= required_qty THEN 1 ELSE 0 END) / COUNT(*) * 100 FROM work_order_kit",
        "unit": "%",
        "data_source": "work_order_kit",
        "refresh_cycle": "周",
    },
    {
        "name": "供应商综合评分",
        "business_meaning": "综合评估供应商履约表现",
        "calculation_formula": "准时交货率 × 0.4 + 质量合格率 × 0.4 + 其他维度 × 0.2",
        "query_logic": "SELECT delivery_on_time_rate * 0.4 + quality_pass_rate * 0.4 + fulfillment_rate * 0.2 FROM supplier_performance",
        "unit": "分",
        "data_source": "supplier_performance",
        "refresh_cycle": "月",
    },
    {
        "name": "对账完成率",
        "business_meaning": "衡量对账结算进度",
        "calculation_formula": "已完成对账结算订单数 / 已完成履约订单数 × 100%",
        "query_logic": "SELECT COUNT(*) FROM settlement_reconciliation WHERE settlement_status IN ('已开票','已付款') / COUNT(*) * 100",
        "unit": "%",
        "data_source": "settlement_reconciliation",
        "refresh_cycle": "月",
    },
    {
        "name": "异常闭环时效",
        "business_meaning": "衡量履约异常处理效率",
        "calculation_formula": "异常订单平均处理闭环时长 = 闭环时间 - 异常发生时间",
        "query_logic": "SELECT AVG(processing_duration_hours) FROM fulfillment_exception WHERE is_closed = 1",
        "unit": "小时",
        "data_source": "fulfillment_exception",
        "refresh_cycle": "月",
    },
    {
        "name": "安全库存不足率",
        "business_meaning": "衡量物料安全库存不足的风险",
        "calculation_formula": "安全库存不足物料数 / 总监控物料数 × 100%",
        "query_logic": "SELECT COUNT(*) FROM forecast_stock WHERE is_safety_stock_insufficient = 1 / COUNT(*) * 100",
        "unit": "%",
        "data_source": "forecast_stock",
        "refresh_cycle": "周",
    },
]

# Finance scenario data
FINANCE_BUSINESS_OBJECTS = [
    {
        "name": "集团营收利润汇总表",
        "description": "记录集团层面的营收、利润、同比环比等关键财务指标",
        "related_entities": json.dumps([{"table": "group_revenue_profit", "role": "header"}], ensure_ascii=False),
        "department": "财务部",
    },
    {
        "name": "业务板块营收利润表",
        "description": "按业务板块（肝素原料药/制剂/CDMO/创新药）记录营收利润",
        "related_entities": json.dumps([{"table": "segment_revenue_profit", "role": "header"}], ensure_ascii=False),
        "department": "财务部",
    },
    {
        "name": "资产负债表",
        "description": "记录期末资产、负债、存货等资产负债信息",
        "related_entities": json.dumps([{"table": "balance_sheet", "role": "header"}], ensure_ascii=False),
        "department": "财务部",
    },
    {
        "name": "现金流量表",
        "description": "记录三大现金流分类归集",
        "related_entities": json.dumps([{"table": "cash_flow", "role": "header"}], ensure_ascii=False),
        "department": "财务部",
    },
]

FINANCE_BUSINESS_RULES = [
    {
        "name": "营收同比变动计算",
        "description": "（本期营收 - 去年同期营收）/ 去年同期营收 × 100%",
        "category": "营收与利润规则",
        "condition_expression": "(current_revenue - prior_year_revenue) / prior_year_revenue * 100",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "毛利率计算",
        "description": "（营收 - 营业成本）/ 营收 × 100%",
        "category": "营收与利润规则",
        "condition_expression": "(operating_revenue - operating_cost) / operating_revenue * 100",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "资产负债率计算",
        "description": "总负债 / 总资产 × 100%",
        "category": "资产负债规则",
        "condition_expression": "total_liability / total_asset * 100",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "经营现金流覆盖倍数",
        "description": "经营活动现金流净额 / 归母净利润",
        "category": "现金流规则",
        "condition_expression": "operating_cash_flow / net_profit_parent",
        "priority": 1,
        "status": "active",
    },
    {
        "name": "预算达成率",
        "description": "实际值 / 预算值 × 100%",
        "category": "预算与投融资规则",
        "condition_expression": "actual_value / budget_value * 100",
        "priority": 1,
        "status": "active",
    },
]

FINANCE_METRICS = [
    {
        "name": "综合毛利率",
        "business_meaning": "衡量集团整体盈利能力",
        "calculation_formula": "（营收 - 营业成本）/ 营收 × 100%",
        "unit": "%",
        "data_source": "group_revenue_profit",
        "refresh_cycle": "月",
    },
    {
        "name": "归母净利率",
        "business_meaning": "衡量归母净利润占营收比重",
        "calculation_formula": "归母净利润 / 营业收入 × 100%",
        "unit": "%",
        "data_source": "group_revenue_profit",
        "refresh_cycle": "月",
    },
    {
        "name": "资产负债率",
        "business_meaning": "衡量企业负债水平和偿债能力",
        "calculation_formula": "总负债 / 总资产 × 100%",
        "unit": "%",
        "data_source": "balance_sheet",
        "refresh_cycle": "季度",
    },
    {
        "name": "ROE",
        "business_meaning": "加权平均净资产收益率",
        "calculation_formula": "归母净利润 / 加权平均净资产 × 100%",
        "unit": "%",
        "data_source": "budget_investment_dividend",
        "refresh_cycle": "年",
    },
]

# Data assets for both scenarios
DATA_ASSETS = [
    {"datasource_name": "test_db", "table_name": "purchase_order", "table_comment": "采购订单主表"},
    {"datasource_name": "test_db", "table_name": "order_material_detail", "table_comment": "订单物料明细表"},
    {"datasource_name": "test_db", "table_name": "inbound_record", "table_comment": "入库记录表"},
    {"datasource_name": "test_db", "table_name": "quality_inspection", "table_comment": "来料质量检验表"},
    {"datasource_name": "test_db", "table_name": "fulfillment_exception", "table_comment": "履约异常表"},
    {"datasource_name": "test_db", "table_name": "logistics_receipt", "table_comment": "物流到货签收表"},
    {"datasource_name": "test_db", "table_name": "settlement_reconciliation", "table_comment": "对账结算表"},
    {"datasource_name": "test_db", "table_name": "supplier_performance", "table_comment": "供应商绩效考核表"},
    {"datasource_name": "test_db", "table_name": "work_order_kit", "table_comment": "生产工单物料齐套表"},
    {"datasource_name": "test_db", "table_name": "forecast_stock", "table_comment": "备货预测表"},
    {"datasource_name": "test_db", "table_name": "group_revenue_profit", "table_comment": "集团营收利润汇总表"},
    {"datasource_name": "test_db", "table_name": "segment_revenue_profit", "table_comment": "业务板块营收利润表"},
    {"datasource_name": "test_db", "table_name": "balance_sheet", "table_comment": "资产负债表"},
    {"datasource_name": "test_db", "table_name": "cash_flow", "table_comment": "现金流量表"},
]


# ════════════════════════════════════════════════════════════════
# Test Classes
# ════════════════════════════════════════════════════════════════


class TestBusinessActivityCRUD:
    """Tests for /api/ontology/activities endpoints."""

    @pytest.mark.asyncio
    async def test_create_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/activities",
            json=MANUFACTURING_BUSINESS_ACTIVITIES[0],
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "采购需求下达"
        assert data["description"] is not None
        assert data["activity_id"] > 0

    @pytest.mark.asyncio
    async def test_list_activities(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create multiple activities
        for act in MANUFACTURING_BUSINESS_ACTIVITIES[:3]:
            await client.post("/api/ontology/activities", json=act, headers=headers)

        resp = await client.get("/api/ontology/activities", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_get_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/activities",
            json=MANUFACTURING_BUSINESS_ACTIVITIES[0],
            headers=headers,
        )
        act_id = create_resp.json()["activity_id"]

        resp = await client.get(f"/api/ontology/activities/{act_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "采购需求下达"

    @pytest.mark.asyncio
    async def test_get_activity_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.get("/api/ontology/activities/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/activities",
            json=MANUFACTURING_BUSINESS_ACTIVITIES[0],
            headers=headers,
        )
        act_id = create_resp.json()["activity_id"]

        resp = await client.put(
            f"/api/ontology/activities/{act_id}",
            json={"description": "Updated description", "updated_by": "tester"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_activity_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.put(
            "/api/ontology/activities/99999",
            json={"name": "Ghost"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "To Delete", "description": "temp"},
            headers=headers,
        )
        act_id = create_resp.json()["activity_id"]

        resp = await client.delete(f"/api/ontology/activities/{act_id}", headers=headers)
        assert resp.status_code == 200

        # Verify deleted
        get_resp = await client.get(f"/api/ontology/activities/{act_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_activity_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.delete("/api/ontology/activities/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_seed_all_manufacturing_activities(self, client: AsyncClient, auth_token: str):
        """Seed all manufacturing business activities from the document."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        created_ids = []
        for act in MANUFACTURING_BUSINESS_ACTIVITIES:
            resp = await client.post("/api/ontology/activities", json=act, headers=headers)
            assert resp.status_code == 200
            created_ids.append(resp.json()["activity_id"])

        assert len(created_ids) == len(MANUFACTURING_BUSINESS_ACTIVITIES)

        # Verify all listed
        list_resp = await client.get("/api/ontology/activities", headers=headers)
        all_activities = list_resp.json()
        names = {a["name"] for a in all_activities}
        for act in MANUFACTURING_BUSINESS_ACTIVITIES:
            assert act["name"] in names


class TestBusinessObjectCRUD:
    """Tests for /api/ontology/objects endpoints."""

    @pytest.mark.asyncio
    async def test_create_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/objects",
            json=MANUFACTURING_BUSINESS_OBJECTS[0],
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "采购订单主表"
        assert data["object_id"] > 0

    @pytest.mark.asyncio
    async def test_list_objects(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        for obj in MANUFACTURING_BUSINESS_OBJECTS[:3]:
            await client.post("/api/ontology/objects", json=obj, headers=headers)

        resp = await client.get("/api/ontology/objects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    @pytest.mark.asyncio
    async def test_get_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/objects",
            json=MANUFACTURING_BUSINESS_OBJECTS[0],
            headers=headers,
        )
        obj_id = create_resp.json()["object_id"]

        resp = await client.get(f"/api/ontology/objects/{obj_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "采购订单主表"

    @pytest.mark.asyncio
    async def test_get_object_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.get("/api/ontology/objects/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/objects",
            json=MANUFACTURING_BUSINESS_OBJECTS[0],
            headers=headers,
        )
        obj_id = create_resp.json()["object_id"]

        resp = await client.put(
            f"/api/ontology/objects/{obj_id}",
            json={"description": "Updated object description"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated object description"

    @pytest.mark.asyncio
    async def test_delete_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/objects",
            json={"name": "Temp Object", "description": "to delete"},
            headers=headers,
        )
        obj_id = create_resp.json()["object_id"]

        resp = await client.delete(f"/api/ontology/objects/{obj_id}", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_seed_all_manufacturing_objects(self, client: AsyncClient, auth_token: str):
        """Seed all manufacturing business objects from the document."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for obj in MANUFACTURING_BUSINESS_OBJECTS:
            resp = await client.post("/api/ontology/objects", json=obj, headers=headers)
            assert resp.status_code == 200

        list_resp = await client.get("/api/ontology/objects", headers=headers)
        all_objects = list_resp.json()
        names = {o["name"] for o in all_objects}
        for obj in MANUFACTURING_BUSINESS_OBJECTS:
            assert obj["name"] in names

    @pytest.mark.asyncio
    async def test_seed_finance_objects(self, client: AsyncClient, auth_token: str):
        """Seed finance scenario business objects."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for obj in FINANCE_BUSINESS_OBJECTS:
            resp = await client.post("/api/ontology/objects", json=obj, headers=headers)
            assert resp.status_code == 200


class TestBusinessRuleCRUD:
    """Tests for /api/ontology/rules endpoints."""

    @pytest.mark.asyncio
    async def test_create_rule(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/rules",
            json=MANUFACTURING_BUSINESS_RULES[0],
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "订单履约率计算"
        assert data["category"] == "履约率规则"

    @pytest.mark.asyncio
    async def test_create_rule_with_associated_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create an activity first
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Test Activity for Rule"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        resp = await client.post(
            "/api/ontology/rules",
            json={
                "name": "Rule with Activity",
                "description": "Test",
                "category": "test",
                "associated_activity_id": act_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["associated_activity_id"] == act_id

    @pytest.mark.asyncio
    async def test_create_rule_with_invalid_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/rules",
            json={
                "name": "Bad Rule",
                "associated_activity_id": 99999,
            },
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_rule_with_associated_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        obj_resp = await client.post(
            "/api/ontology/objects",
            json={"name": "Test Object for Rule"},
            headers=headers,
        )
        obj_id = obj_resp.json()["object_id"]

        resp = await client.post(
            "/api/ontology/rules",
            json={
                "name": "Rule with Object",
                "associated_object_id": obj_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["associated_object_id"] == obj_id

    @pytest.mark.asyncio
    async def test_list_rules(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        for rule in MANUFACTURING_BUSINESS_RULES[:3]:
            await client.post("/api/ontology/rules", json=rule, headers=headers)

        resp = await client.get("/api/ontology/rules", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    @pytest.mark.asyncio
    async def test_get_rule(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/rules",
            json=MANUFACTURING_BUSINESS_RULES[0],
            headers=headers,
        )
        rule_id = create_resp.json()["rule_id"]

        resp = await client.get(f"/api/ontology/rules/{rule_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "订单履约率计算"

    @pytest.mark.asyncio
    async def test_update_rule(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/rules",
            json=MANUFACTURING_BUSINESS_RULES[0],
            headers=headers,
        )
        rule_id = create_resp.json()["rule_id"]

        resp = await client.put(
            f"/api/ontology/rules/{rule_id}",
            json={"description": "Updated rule description", "status": "inactive"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated rule description"
        assert resp.json()["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_delete_rule(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/rules",
            json={"name": "Rule to Delete"},
            headers=headers,
        )
        rule_id = create_resp.json()["rule_id"]

        resp = await client.delete(f"/api/ontology/rules/{rule_id}", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_seed_all_manufacturing_rules(self, client: AsyncClient, auth_token: str):
        """Seed all manufacturing business rules from the document."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for rule in MANUFACTURING_BUSINESS_RULES:
            resp = await client.post("/api/ontology/rules", json=rule, headers=headers)
            assert resp.status_code == 200

        list_resp = await client.get("/api/ontology/rules", headers=headers)
        names = {r["name"] for r in list_resp.json()}
        for rule in MANUFACTURING_BUSINESS_RULES:
            assert rule["name"] in names

    @pytest.mark.asyncio
    async def test_seed_finance_rules(self, client: AsyncClient, auth_token: str):
        """Seed finance scenario business rules."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for rule in FINANCE_BUSINESS_RULES:
            resp = await client.post("/api/ontology/rules", json=rule, headers=headers)
            assert resp.status_code == 200


class TestMetricCRUD:
    """Tests for /api/ontology/metrics endpoints."""

    @pytest.mark.asyncio
    async def test_create_metric(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/metrics",
            json=MANUFACTURING_METRICS[0],
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "订单履约率"
        assert data["unit"] == "%"
        assert data["data_source"] == "purchase_order"

    @pytest.mark.asyncio
    async def test_list_metrics(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        for m in MANUFACTURING_METRICS[:3]:
            await client.post("/api/ontology/metrics", json=m, headers=headers)

        resp = await client.get("/api/ontology/metrics", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    @pytest.mark.asyncio
    async def test_get_metric(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/metrics",
            json=MANUFACTURING_METRICS[0],
            headers=headers,
        )
        metric_id = create_resp.json()["metric_id"]

        resp = await client.get(f"/api/ontology/metrics/{metric_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "订单履约率"

    @pytest.mark.asyncio
    async def test_update_metric(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/metrics",
            json=MANUFACTURING_METRICS[0],
            headers=headers,
        )
        metric_id = create_resp.json()["metric_id"]

        resp = await client.put(
            f"/api/ontology/metrics/{metric_id}",
            json={"business_meaning": "Updated meaning", "unit": "分"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["unit"] == "分"

    @pytest.mark.asyncio
    async def test_delete_metric(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/metrics",
            json={"name": "Temp Metric"},
            headers=headers,
        )
        metric_id = create_resp.json()["metric_id"]

        resp = await client.delete(f"/api/ontology/metrics/{metric_id}", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_seed_all_manufacturing_metrics(self, client: AsyncClient, auth_token: str):
        """Seed all manufacturing metrics from the document."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for m in MANUFACTURING_METRICS:
            resp = await client.post("/api/ontology/metrics", json=m, headers=headers)
            assert resp.status_code == 200

        list_resp = await client.get("/api/ontology/metrics", headers=headers)
        names = {m["name"] for m in list_resp.json()}
        for m in MANUFACTURING_METRICS:
            assert m["name"] in names

    @pytest.mark.asyncio
    async def test_seed_finance_metrics(self, client: AsyncClient, auth_token: str):
        """Seed finance scenario metrics."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for m in FINANCE_METRICS:
            resp = await client.post("/api/ontology/metrics", json=m, headers=headers)
            assert resp.status_code == 200


class TestObjectRelationshipCRUD:
    """Tests for /api/ontology/object-relationships endpoints."""

    @pytest.mark.asyncio
    async def test_create_relationship(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create two objects first
        obj1 = await client.post(
            "/api/ontology/objects",
            json={"name": "Object A"},
            headers=headers,
        )
        obj2 = await client.post(
            "/api/ontology/objects",
            json={"name": "Object B"},
            headers=headers,
        )
        id1 = obj1.json()["object_id"]
        id2 = obj2.json()["object_id"]

        resp = await client.post(
            "/api/ontology/object-relationships",
            json={
                "object_id_1": id1,
                "object_id_2": id2,
                "relationship_type": "1:N",
                "join_logic": "purchase_order.order_id = order_material_detail.order_id",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["object_id_1"] == id1
        assert data["object_id_2"] == id2
        assert data["relationship_type"] == "1:N"

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_object(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/object-relationships",
            json={
                "object_id_1": 99999,
                "object_id_2": 99998,
                "relationship_type": "1:1",
            },
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_relationships(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        obj1 = await client.post("/api/ontology/objects", json={"name": "Obj1"}, headers=headers)
        obj2 = await client.post("/api/ontology/objects", json={"name": "Obj2"}, headers=headers)
        id1, id2 = obj1.json()["object_id"], obj2.json()["object_id"]

        await client.post(
            "/api/ontology/object-relationships",
            json={"object_id_1": id1, "object_id_2": id2, "relationship_type": "N:1"},
            headers=headers,
        )

        resp = await client.get("/api/ontology/object-relationships", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_delete_relationship(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        obj1 = await client.post("/api/ontology/objects", json={"name": "Del1"}, headers=headers)
        obj2 = await client.post("/api/ontology/objects", json={"name": "Del2"}, headers=headers)
        id1, id2 = obj1.json()["object_id"], obj2.json()["object_id"]

        create_resp = await client.post(
            "/api/ontology/object-relationships",
            json={"object_id_1": id1, "object_id_2": id2},
            headers=headers,
        )
        rel_id = create_resp.json()["relationship_id"]

        resp = await client.delete(
            f"/api/ontology/object-relationships/{rel_id}", headers=headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_relationship_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.delete("/api/ontology/object-relationships/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_manufacturing_table_relationships(self, client: AsyncClient, auth_token: str):
        """Create relationships between manufacturing tables as defined in the document."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create all manufacturing objects
        obj_ids = {}
        for obj in MANUFACTURING_BUSINESS_OBJECTS:
            resp = await client.post("/api/ontology/objects", json=obj, headers=headers)
            obj_ids[obj["name"]] = resp.json()["object_id"]

        # Create key relationships from the document
        relationships = [
            ("采购订单主表", "订单物料明细表", "1:N", "purchase_order.order_id = order_material_detail.order_id"),
            ("采购订单主表", "入库记录表", "1:N", "purchase_order.order_id = inbound_record.order_id"),
            ("采购订单主表", "来料质量检验表", "1:N", "purchase_order.order_id = quality_inspection.order_id"),
            ("采购订单主表", "履约异常表", "1:N", "purchase_order.order_id = fulfillment_exception.order_id"),
            ("采购订单主表", "物流到货签收表", "1:N", "purchase_order.order_id = logistics_receipt.order_id"),
            ("采购订单主表", "对账结算表", "1:N", "purchase_order.order_id = settlement_reconciliation.order_id"),
            ("采购订单主表", "供应商绩效考核表", "N:1", "purchase_order.supplier_id = supplier_performance.supplier_id"),
        ]

        for name1, name2, rel_type, join_logic in relationships:
            resp = await client.post(
                "/api/ontology/object-relationships",
                json={
                    "object_id_1": obj_ids[name1],
                    "object_id_2": obj_ids[name2],
                    "relationship_type": rel_type,
                    "join_logic": join_logic,
                },
                headers=headers,
            )
            assert resp.status_code == 200


class TestActivityMetricRelationCRUD:
    """Tests for /api/ontology/activity-metric-rels endpoints."""

    @pytest.mark.asyncio
    async def test_create_relation(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create activity and metric
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Test Activity"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        metric_resp = await client.post(
            "/api/ontology/metrics",
            json={"name": "Test Metric", "unit": "%"},
            headers=headers,
        )
        metric_id = metric_resp.json()["metric_id"]

        resp = await client.post(
            "/api/ontology/activity-metric-rels",
            json={"activity_id": act_id, "metric_id": metric_id, "usage_stage": "output"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_id"] == act_id
        assert data["metric_id"] == metric_id

    @pytest.mark.asyncio
    async def test_create_relation_invalid_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        metric_resp = await client.post(
            "/api/ontology/metrics",
            json={"name": "Metric2"},
            headers=headers,
        )
        metric_id = metric_resp.json()["metric_id"]

        resp = await client.post(
            "/api/ontology/activity-metric-rels",
            json={"activity_id": 99999, "metric_id": metric_id},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_relation_invalid_metric(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity2"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        resp = await client.post(
            "/api/ontology/activity-metric-rels",
            json={"activity_id": act_id, "metric_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_relations_by_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity3"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        m1 = await client.post("/api/ontology/metrics", json={"name": "M1"}, headers=headers)
        m2 = await client.post("/api/ontology/metrics", json={"name": "M2"}, headers=headers)

        await client.post(
            "/api/ontology/activity-metric-rels",
            json={"activity_id": act_id, "metric_id": m1.json()["metric_id"]},
            headers=headers,
        )
        await client.post(
            "/api/ontology/activity-metric-rels",
            json={"activity_id": act_id, "metric_id": m2.json()["metric_id"]},
            headers=headers,
        )

        resp = await client.get(
            f"/api/ontology/activity-metric-rels?activity_id={act_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_delete_relation(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity4"},
            headers=headers,
        )
        m_resp = await client.post(
            "/api/ontology/metrics",
            json={"name": "M3"},
            headers=headers,
        )

        create_resp = await client.post(
            "/api/ontology/activity-metric-rels",
            json={
                "activity_id": act_resp.json()["activity_id"],
                "metric_id": m_resp.json()["metric_id"],
            },
            headers=headers,
        )
        rel_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/ontology/activity-metric-rels/{rel_id}", headers=headers
        )
        assert resp.status_code == 200


class TestActivityEntityRelationCRUD:
    """Tests for /api/ontology/activity-entity-rels endpoints."""

    @pytest.mark.asyncio
    async def test_create_relation(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity for Entity"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        resp = await client.post(
            "/api/ontology/activity-entity-rels",
            json={
                "activity_id": act_id,
                "entity_name": "purchase_order",
                "entity_type": "OUTPUT",
                "order_index": 0,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_name"] == "purchase_order"
        assert data["entity_type"] == "OUTPUT"

    @pytest.mark.asyncio
    async def test_create_relation_invalid_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/activity-entity-rels",
            json={"activity_id": 99999, "entity_name": "test_table"},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_relations_by_activity(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity for Entity List"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        await client.post(
            "/api/ontology/activity-entity-rels",
            json={"activity_id": act_id, "entity_name": "table_a", "entity_type": "INPUT"},
            headers=headers,
        )
        await client.post(
            "/api/ontology/activity-entity-rels",
            json={"activity_id": act_id, "entity_name": "table_b", "entity_type": "OUTPUT"},
            headers=headers,
        )

        resp = await client.get(
            f"/api/ontology/activity-entity-rels?activity_id={act_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_delete_relation(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        act_resp = await client.post(
            "/api/ontology/activities",
            json={"name": "Activity for Entity Del"},
            headers=headers,
        )
        act_id = act_resp.json()["activity_id"]

        create_resp = await client.post(
            "/api/ontology/activity-entity-rels",
            json={"activity_id": act_id, "entity_name": "to_delete"},
            headers=headers,
        )
        rel_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/ontology/activity-entity-rels/{rel_id}", headers=headers
        )
        assert resp.status_code == 200


class TestDataAssetCRUD:
    """Tests for /api/ontology/data-assets endpoints."""

    @pytest.mark.asyncio
    async def test_create_data_asset(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(
            "/api/ontology/data-assets",
            json=DATA_ASSETS[0],
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["table_name"] == "purchase_order"
        assert data["datasource_name"] == "test_db"

    @pytest.mark.asyncio
    async def test_create_duplicate_data_asset(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/ontology/data-assets", json=DATA_ASSETS[0], headers=headers)

        # Duplicate should fail with 409
        resp = await client.post("/api/ontology/data-assets", json=DATA_ASSETS[0], headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_data_assets(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        for asset in DATA_ASSETS[:3]:
            await client.post("/api/ontology/data-assets", json=asset, headers=headers)

        resp = await client.get("/api/ontology/data-assets", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    @pytest.mark.asyncio
    async def test_delete_data_asset(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_resp = await client.post(
            "/api/ontology/data-assets",
            json={"datasource_name": "test_db", "table_name": "temp_table", "table_comment": "temp"},
            headers=headers,
        )
        asset_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/ontology/data-assets/{asset_id}", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_data_asset_not_found(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.delete("/api/ontology/data-assets/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_seed_all_data_assets(self, client: AsyncClient, auth_token: str):
        """Seed all data assets from both scenarios."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        for asset in DATA_ASSETS:
            resp = await client.post("/api/ontology/data-assets", json=asset, headers=headers)
            assert resp.status_code == 200

        list_resp = await client.get("/api/ontology/data-assets", headers=headers)
        table_names = {a["table_name"] for a in list_resp.json()}
        for asset in DATA_ASSETS:
            assert asset["table_name"] in table_names


class TestOntologyAuthentication:
    """Tests that ontology endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_activities_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/ontology/activities")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_objects_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/ontology/objects")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_rules_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/ontology/rules")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_metrics_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/ontology/metrics")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_data_assets_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/ontology/data-assets")
        assert resp.status_code in (401, 403)


class TestCrossScenarioRelationships:
    """Tests for cross-scenario relationships defined in the document (Part 3)."""

    @pytest.mark.asyncio
    async def test_supply_chain_to_finance_link(self, client: AsyncClient, auth_token: str):
        """Test creating relationships between supply chain and finance objects."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create supply chain objects
        sc_obj = await client.post(
            "/api/ontology/objects",
            json=MANUFACTURING_BUSINESS_OBJECTS[0],  # 采购订单主表
            headers=headers,
        )
        # Create finance objects
        fin_obj = await client.post(
            "/api/ontology/objects",
            json=FINANCE_BUSINESS_OBJECTS[1],  # 业务板块营收利润表
            headers=headers,
        )

        sc_id = sc_obj.json()["object_id"]
        fin_id = fin_obj.json()["object_id"]

        # Create cross-scenario relationship: 采购金额 → 营业成本
        resp = await client.post(
            "/api/ontology/object-relationships",
            json={
                "object_id_1": sc_id,
                "object_id_2": fin_id,
                "relationship_type": "N:1",
                "join_logic": "purchase_order.total_amount contributes to segment_revenue_profit.operating_cost",
                "constraint_logic": "purchase_order.factory = segment_revenue_profit.segment_name",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["relationship_type"] == "N:1"
        assert data["join_logic"] is not None

    @pytest.mark.asyncio
    async def test_settlement_to_balance_sheet_link(self, client: AsyncClient, auth_token: str):
        """Test creating relationship: 应付账款 → 负债 (settlement → balance_sheet)."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        settlement_obj = await client.post(
            "/api/ontology/objects",
            json=MANUFACTURING_BUSINESS_OBJECTS[6],  # 对账结算表
            headers=headers,
        )
        balance_obj = await client.post(
            "/api/ontology/objects",
            json=FINANCE_BUSINESS_OBJECTS[2],  # 资产负债表
            headers=headers,
        )

        resp = await client.post(
            "/api/ontology/object-relationships",
            json={
                "object_id_1": settlement_obj.json()["object_id"],
                "object_id_2": balance_obj.json()["object_id"],
                "relationship_type": "N:1",
                "join_logic": "settlement_reconciliation.unpaid_amount → balance_sheet.accounts_payable",
            },
            headers=headers,
        )
        assert resp.status_code == 200
