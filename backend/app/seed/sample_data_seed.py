"""
Auto-seed sample data for manufacturing supplier order fulfillment scenario.

Called at startup to ensure sample business tables, data, and ontology
entries exist without requiring manual SQL execution.

CLI usage:
    python -m app.seed.sample_data_seed          # seed if empty
    python -m app.seed.sample_data_seed --reset  # clean and re-seed
    python -m app.seed.sample_data_seed --clean  # only clean
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.business_models import (
    ForecastStockModel,
    FulfillmentExceptionModel,
    InboundRecordModel,
    LogisticsReceiptModel,
    OrderMaterialDetailModel,
    PurchaseOrderModel,
    QualityInspectionModel,
    SettlementReconciliationModel,
    SupplierPerformanceModel,
    WorkOrderKitModel,
)
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

DEFAULT_TENANT_ID = 1


async def _table_is_empty(session: AsyncSession, table_name: str) -> bool:
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM {table_name}")
    )
    return result.scalar() == 0


# ════════════════════════════════════════════════════════════════════════════
# Seeding
# ════════════════════════════════════════════════════════════════════════════

async def init_sample_data(force: bool = False) -> None:
    async with async_session_factory() as session:
        te = await session.execute(
            text("SELECT 1 FROM tenants WHERE id = :tid"), {"tid": DEFAULT_TENANT_ID}
        )
        if te.fetchone() is None:
            logger.warning("Default tenant not found, skipping seed")
            return

        need_business = force or await _table_is_empty(session, "purchase_order")
        need_ontology = force or await _table_is_empty(session, "data_asset")

        logger.info("Seed check: business=%s, ontology=%s, force=%s",
                     need_business, need_ontology, force)

        if not need_business and not need_ontology:
            logger.info("Sample data already exists, skipping seed")
            return

        if need_business:
            await _seed_business_data(session)
            logger.info("Business data seeded")

        if need_ontology:
            await _seed_ontology(session)
            logger.info("Ontology data seeded")

        await session.commit()

        po_count = (await session.execute(text("SELECT COUNT(*) FROM purchase_order"))).scalar()
        asset_count = (await session.execute(text("SELECT COUNT(*) FROM data_asset"))).scalar()
        obj_count = (await session.execute(text("SELECT COUNT(*) FROM business_object"))).scalar()
        act_count = (await session.execute(text("SELECT COUNT(*) FROM business_activity"))).scalar()
        logger.info("Seed verification: orders=%d, assets=%d, objects=%d, activities=%d",
                     po_count, asset_count, obj_count, act_count)


async def _seed_business_data(session: AsyncSession) -> None:
    logger.info("Seeding business data...")

    await session.execute(insert(PurchaseOrderModel), [
        {"order_id":"PO-2024-001","supplier_id":"SUP001","supplier_name":"苏州精密五金有限公司","supplier_grade":"A","supplier_type":"战略","supplier_region":"本地","order_type":"常规","order_status":"全部到货","order_date":date(2024,1,5),"plan_delivery_date":date(2024,1,20),"actual_delivery_date":date(2024,1,19),"plan_delivery_qty":5000,"actual_delivery_qty":5000,"total_amount":125000,"currency":"CNY","factory":"一分厂","purchaser_id":"P001","purchaser_name":"张三","is_fulfillment_ok":True,"fulfillment_rate":100,"on_time_flag":"准时","overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":True},
        {"order_id":"PO-2024-002","supplier_id":"SUP001","supplier_name":"苏州精密五金有限公司","supplier_grade":"A","supplier_type":"战略","supplier_region":"本地","order_type":"紧急","order_status":"全部到货","order_date":date(2024,1,10),"plan_delivery_date":date(2024,1,15),"actual_delivery_date":date(2024,1,16),"plan_delivery_qty":2000,"actual_delivery_qty":2000,"total_amount":58000,"currency":"CNY","factory":"二分厂","purchaser_id":"P002","purchaser_name":"李四","is_fulfillment_ok":True,"fulfillment_rate":95,"on_time_flag":"逾期","overdue_days":1,"plan_delivery_date_change_count":0,"is_closed":True},
        {"order_id":"PO-2024-003","supplier_id":"SUP002","supplier_name":"深圳鸿达电子有限公司","supplier_grade":"B","supplier_type":"备选","supplier_region":"本地","order_type":"常规","order_status":"部分到货","order_date":date(2024,2,1),"plan_delivery_date":date(2024,2,15),"actual_delivery_date":None,"plan_delivery_qty":10000,"actual_delivery_qty":7000,"total_amount":300000,"currency":"CNY","factory":"一分厂","purchaser_id":"P001","purchaser_name":"张三","is_fulfillment_ok":False,"fulfillment_rate":70,"on_time_flag":None,"overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":False},
        {"order_id":"PO-2024-004","supplier_id":"SUP003","supplier_name":"东莞华丰包材有限公司","supplier_grade":"B","supplier_type":"备选","supplier_region":"异地","order_type":"常规","order_status":"全部到货","order_date":date(2024,2,5),"plan_delivery_date":date(2024,2,25),"actual_delivery_date":date(2024,2,22),"plan_delivery_qty":3000,"actual_delivery_qty":3000,"total_amount":45000,"currency":"CNY","factory":"二分厂","purchaser_id":"P003","purchaser_name":"王五","is_fulfillment_ok":True,"fulfillment_rate":100,"on_time_flag":"提前","overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":True},
        {"order_id":"PO-2024-005","supplier_id":"SUP001","supplier_name":"苏州精密五金有限公司","supplier_grade":"A","supplier_type":"战略","supplier_region":"本地","order_type":"备货","order_status":"全部到货","order_date":date(2024,3,1),"plan_delivery_date":date(2024,3,20),"actual_delivery_date":date(2024,3,18),"plan_delivery_qty":8000,"actual_delivery_qty":8000,"total_amount":200000,"currency":"CNY","factory":"一分厂","purchaser_id":"P001","purchaser_name":"张三","is_fulfillment_ok":True,"fulfillment_rate":100,"on_time_flag":"提前","overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":True},
        {"order_id":"PO-2024-006","supplier_id":"SUP002","supplier_name":"深圳鸿达电子有限公司","supplier_grade":"B","supplier_type":"备选","supplier_region":"本地","order_type":"紧急","order_status":"未发货","order_date":date(2024,3,10),"plan_delivery_date":date(2024,3,20),"actual_delivery_date":None,"plan_delivery_qty":4000,"actual_delivery_qty":0,"total_amount":120000,"currency":"CNY","factory":"二分厂","purchaser_id":"P002","purchaser_name":"李四","is_fulfillment_ok":False,"fulfillment_rate":None,"on_time_flag":None,"overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":False},
        {"order_id":"PO-2024-007","supplier_id":"SUP003","supplier_name":"东莞华丰包材有限公司","supplier_grade":"B","supplier_type":"备选","supplier_region":"异地","order_type":"常规","order_status":"已关闭","order_date":date(2024,3,15),"plan_delivery_date":date(2024,4,1),"actual_delivery_date":None,"plan_delivery_qty":5000,"actual_delivery_qty":5000,"total_amount":75000,"currency":"CNY","factory":"一分厂","purchaser_id":"P003","purchaser_name":"王五","is_fulfillment_ok":False,"fulfillment_rate":None,"on_time_flag":None,"overdue_days":0,"plan_delivery_date_change_count":0,"is_closed":True},
    ])

    await session.execute(insert(OrderMaterialDetailModel), [
        {"detail_id":"DET-001","order_id":"PO-2024-001","material_id":"MAT-001","material_name":"M4不锈钢螺栓","material_category":"五金件","is_key_material":True,"plan_qty":3000,"actual_qty":3000,"gap_qty":0,"unit_price":15,"amount":45000,"standard_lead_time_days":7,"actual_lead_time_days":7,"batch_delivery_count":1,"is_inspection_exempt":False,"inspection_type":"抽检"},
        {"detail_id":"DET-002","order_id":"PO-2024-001","material_id":"MAT-002","material_name":"PCB电路板V2","material_category":"核心零部件","is_key_material":True,"plan_qty":2000,"actual_qty":2000,"gap_qty":0,"unit_price":40,"amount":80000,"standard_lead_time_days":14,"actual_lead_time_days":14,"batch_delivery_count":1,"is_inspection_exempt":False,"inspection_type":"全检"},
        {"detail_id":"DET-003","order_id":"PO-2024-002","material_id":"MAT-003","material_name":"散热铝型材","material_category":"原材料","is_key_material":False,"plan_qty":2000,"actual_qty":2000,"gap_qty":0,"unit_price":29,"amount":58000,"standard_lead_time_days":10,"actual_lead_time_days":11,"batch_delivery_count":1,"is_inspection_exempt":True,"inspection_type":"免检"},
        {"detail_id":"DET-004","order_id":"PO-2024-003","material_id":"MAT-001","material_name":"M4不锈钢螺栓","material_category":"五金件","is_key_material":True,"plan_qty":6000,"actual_qty":4000,"gap_qty":2000,"unit_price":15,"amount":90000,"standard_lead_time_days":7,"actual_lead_time_days":None,"batch_delivery_count":2,"is_inspection_exempt":False,"inspection_type":"抽检"},
        {"detail_id":"DET-005","order_id":"PO-2024-003","material_id":"MAT-004","material_name":"PE包装袋","material_category":"包材","is_key_material":False,"plan_qty":4000,"actual_qty":3000,"gap_qty":1000,"unit_price":5,"amount":20000,"standard_lead_time_days":3,"actual_lead_time_days":None,"batch_delivery_count":2,"is_inspection_exempt":True,"inspection_type":"免检"},
        {"detail_id":"DET-006","order_id":"PO-2024-004","material_id":"MAT-004","material_name":"PE包装袋","material_category":"包材","is_key_material":False,"plan_qty":3000,"actual_qty":3000,"gap_qty":0,"unit_price":5,"amount":15000,"standard_lead_time_days":3,"actual_lead_time_days":3,"batch_delivery_count":1,"is_inspection_exempt":True,"inspection_type":"免检"},
        {"detail_id":"DET-007","order_id":"PO-2024-005","material_id":"MAT-001","material_name":"M4不锈钢螺栓","material_category":"五金件","is_key_material":True,"plan_qty":5000,"actual_qty":5000,"gap_qty":0,"unit_price":15,"amount":75000,"standard_lead_time_days":7,"actual_lead_time_days":6,"batch_delivery_count":1,"is_inspection_exempt":False,"inspection_type":"抽检"},
        {"detail_id":"DET-008","order_id":"PO-2024-005","material_id":"MAT-002","material_name":"PCB电路板V2","material_category":"核心零部件","is_key_material":True,"plan_qty":3000,"actual_qty":3000,"gap_qty":0,"unit_price":40,"amount":120000,"standard_lead_time_days":14,"actual_lead_time_days":13,"batch_delivery_count":1,"is_inspection_exempt":False,"inspection_type":"全检"},
        {"detail_id":"DET-009","order_id":"PO-2024-006","material_id":"MAT-002","material_name":"PCB电路板V2","material_category":"核心零部件","is_key_material":True,"plan_qty":4000,"actual_qty":0,"gap_qty":4000,"unit_price":30,"amount":120000,"standard_lead_time_days":14,"actual_lead_time_days":None,"batch_delivery_count":0,"is_inspection_exempt":False,"inspection_type":"全检"},
    ])

    await session.execute(insert(InboundRecordModel), [
        {"inbound_id":"IN-001","order_id":"PO-2024-001","detail_id":"DET-001","material_id":"MAT-001","supplier_id":"SUP001","inbound_type":"正常入库","inbound_qty":3000,"inbound_amount":45000,"inbound_date":date(2024,1,19),"warehouse_id":"WH-A01","plan_inbound_qty":3000},
        {"inbound_id":"IN-002","order_id":"PO-2024-001","detail_id":"DET-002","material_id":"MAT-002","supplier_id":"SUP001","inbound_type":"正常入库","inbound_qty":2000,"inbound_amount":80000,"inbound_date":date(2024,1,19),"warehouse_id":"WH-A02","plan_inbound_qty":2000},
        {"inbound_id":"IN-003","order_id":"PO-2024-002","detail_id":"DET-003","material_id":"MAT-003","supplier_id":"SUP001","inbound_type":"正常入库","inbound_qty":2000,"inbound_amount":58000,"inbound_date":date(2024,1,16),"warehouse_id":"WH-B01","plan_inbound_qty":2000},
        {"inbound_id":"IN-004","order_id":"PO-2024-003","detail_id":"DET-004","material_id":"MAT-001","supplier_id":"SUP002","inbound_type":"正常入库","inbound_qty":4000,"inbound_amount":60000,"inbound_date":date(2024,2,20),"warehouse_id":"WH-A01","plan_inbound_qty":4000},
        {"inbound_id":"IN-005","order_id":"PO-2024-004","detail_id":"DET-006","material_id":"MAT-004","supplier_id":"SUP003","inbound_type":"正常入库","inbound_qty":3000,"inbound_amount":15000,"inbound_date":date(2024,2,22),"warehouse_id":"WH-B02","plan_inbound_qty":3000},
        {"inbound_id":"IN-006","order_id":"PO-2024-005","detail_id":"DET-007","material_id":"MAT-001","supplier_id":"SUP001","inbound_type":"正常入库","inbound_qty":5000,"inbound_amount":75000,"inbound_date":date(2024,3,18),"warehouse_id":"WH-A01","plan_inbound_qty":5000},
        {"inbound_id":"IN-007","order_id":"PO-2024-005","detail_id":"DET-008","material_id":"MAT-002","supplier_id":"SUP001","inbound_type":"正常入库","inbound_qty":3000,"inbound_amount":120000,"inbound_date":date(2024,3,18),"warehouse_id":"WH-A02","plan_inbound_qty":3000},
    ])

    await session.execute(insert(QualityInspectionModel), [
        {"inspection_id":"QC-001","order_id":"PO-2024-001","detail_id":"DET-001","material_id":"MAT-001","supplier_id":"SUP001","inspection_date":date(2024,1,19),"inspection_result":"合格"},
        {"inspection_id":"QC-002","order_id":"PO-2024-001","detail_id":"DET-002","material_id":"MAT-002","supplier_id":"SUP001","inspection_date":date(2024,1,19),"inspection_result":"合格"},
        {"inspection_id":"QC-003","order_id":"PO-2024-002","detail_id":"DET-003","material_id":"MAT-003","supplier_id":"SUP001","inspection_date":date(2024,1,16),"inspection_result":"合格"},
        {"inspection_id":"QC-004","order_id":"PO-2024-003","detail_id":"DET-004","material_id":"MAT-001","supplier_id":"SUP002","inspection_date":date(2024,2,20),"inspection_result":"不合格","defect_type":"尺寸偏差","defect_qty":200,"defect_rate":0.05,"handle_method":"返工"},
        {"inspection_id":"QC-005","order_id":"PO-2024-004","detail_id":"DET-006","material_id":"MAT-004","supplier_id":"SUP003","inspection_date":date(2024,2,22),"inspection_result":"合格"},
        {"inspection_id":"QC-006","order_id":"PO-2024-005","detail_id":"DET-007","material_id":"MAT-001","supplier_id":"SUP001","inspection_date":date(2024,3,18),"inspection_result":"合格"},
        {"inspection_id":"QC-007","order_id":"PO-2024-005","detail_id":"DET-008","material_id":"MAT-002","supplier_id":"SUP001","inspection_date":date(2024,3,18),"inspection_result":"不合格","defect_type":"外观缺陷","defect_qty":50,"defect_rate":0.0167,"handle_method":"特采放行"},
    ])

    await session.execute(insert(FulfillmentExceptionModel), [
        {"exception_id":"EX-001","order_id":"PO-2024-002","supplier_id":"SUP001","exception_type":"交期延误","exception_date":date(2024,1,16),"exception_desc":"受物流堵车影响","is_closed":True,"close_date":date(2024,1,17),"processing_duration_hours":24,"need_manual_intervention":True,"is_external_factor":True},
        {"exception_id":"EX-002","order_id":"PO-2024-003","supplier_id":"SUP002","exception_type":"数量短装","exception_date":date(2024,2,15),"exception_desc":"计划10000实到7000"},
        {"exception_id":"EX-003","order_id":"PO-2024-003","supplier_id":"SUP002","exception_type":"质量不良","exception_date":date(2024,2,20),"exception_desc":"尺寸偏差不良率5%"},
        {"exception_id":"EX-004","order_id":"PO-2024-005","supplier_id":"SUP001","exception_type":"质量不良","exception_date":date(2024,3,18),"exception_desc":"外观缺陷不良率1.67%","is_closed":True,"close_date":date(2024,3,19),"processing_duration_hours":4,"need_manual_intervention":False},
    ])

    await session.execute(insert(LogisticsReceiptModel), [
        {"receipt_id":"LOG-001","order_id":"PO-2024-001","logistics_type":"整车","shipping_region":"本地","plan_arrival_date":date(2024,1,19),"actual_arrival_date":date(2024,1,19)},
        {"receipt_id":"LOG-002","order_id":"PO-2024-002","logistics_type":"快递","shipping_region":"本地","plan_arrival_date":date(2024,1,15),"actual_arrival_date":date(2024,1,16),"is_delayed":True,"delay_hours":24},
        {"receipt_id":"LOG-003","order_id":"PO-2024-003","logistics_type":"整车","shipping_region":"本地","plan_arrival_date":date(2024,2,15),"actual_arrival_date":date(2024,2,20),"is_delayed":True,"delay_hours":120},
        {"receipt_id":"LOG-004","order_id":"PO-2024-004","logistics_type":"零担","shipping_region":"省外","plan_arrival_date":date(2024,2,22),"actual_arrival_date":date(2024,2,22)},
        {"receipt_id":"LOG-005","order_id":"PO-2024-005","logistics_type":"整车","shipping_region":"本地","plan_arrival_date":date(2024,3,18),"actual_arrival_date":date(2024,3,18)},
    ])

    await session.execute(insert(SettlementReconciliationModel), [
        {"settlement_id":"STL-001","order_id":"PO-2024-001","supplier_id":"SUP001","settlement_status":"已付款","invoice_amount":125000,"payment_amount":125000,"payment_date":date(2024,2,20),"payment_cycle_days":30,"fulfillment_ok":True},
        {"settlement_id":"STL-002","order_id":"PO-2024-002","supplier_id":"SUP001","settlement_status":"已付款","invoice_amount":58000,"payment_amount":58000,"payment_date":date(2024,2,15),"payment_cycle_days":30,"fulfillment_ok":True},
        {"settlement_id":"STL-003","order_id":"PO-2024-003","supplier_id":"SUP002","settlement_status":"已对账未开票","invoice_amount":300000,"payment_amount":0,"is_payment_held":True},
        {"settlement_id":"STL-004","order_id":"PO-2024-004","supplier_id":"SUP003","settlement_status":"已开票","invoice_amount":45000,"payment_amount":45000,"payment_date":date(2024,3,25),"payment_cycle_days":30,"fulfillment_ok":True},
        {"settlement_id":"STL-005","order_id":"PO-2024-005","supplier_id":"SUP001","settlement_status":"已付款","invoice_amount":200000,"payment_amount":200000,"payment_date":date(2024,4,18),"payment_cycle_days":30,"fulfillment_ok":True},
    ])

    await session.execute(insert(SupplierPerformanceModel), [
        {"performance_id":"PERF-001","supplier_id":"SUP001","supplier_name":"苏州精密五金有限公司","period":"2024-Q1","comprehensive_score":92.5,"delivery_on_time_rate":0.95,"quality_pass_rate":0.98,"fulfillment_rate":0.98,"supplier_grade":"A","supply_amount":383000,"total_purchase_amount":383000,"score_change":1.5},
        {"performance_id":"PERF-002","supplier_id":"SUP002","supplier_name":"深圳鸿达电子有限公司","period":"2024-Q1","comprehensive_score":68,"delivery_on_time_rate":0.5,"quality_pass_rate":0.8,"fulfillment_rate":0.7,"supplier_grade":"C","is_need_interview":True,"supply_amount":210000,"total_purchase_amount":420000,"score_change":-3},
        {"performance_id":"PERF-003","supplier_id":"SUP003","supplier_name":"东莞华丰包材有限公司","period":"2024-Q1","comprehensive_score":88,"delivery_on_time_rate":1,"quality_pass_rate":1,"fulfillment_rate":1,"supplier_grade":"B","supply_amount":60000,"total_purchase_amount":120000,"score_change":2},
    ])

    await session.execute(insert(WorkOrderKitModel), [
        {"kit_id":"KIT-001","work_order_id":"WO-2024-001","material_id":"MAT-001","material_category":"五金件","required_qty":2000,"available_qty":2000,"kit_rate":1,"is_key_material":True},
        {"kit_id":"KIT-002","work_order_id":"WO-2024-001","material_id":"MAT-002","material_category":"核心零部件","required_qty":1500,"available_qty":1500,"kit_rate":1,"is_key_material":True},
        {"kit_id":"KIT-003","work_order_id":"WO-2024-002","material_id":"MAT-001","material_category":"五金件","required_qty":3000,"available_qty":1000,"kit_rate":0.3333,"is_key_material":True,"is_cause_work_stop":True},
        {"kit_id":"KIT-004","work_order_id":"WO-2024-002","material_id":"MAT-002","material_category":"核心零部件","required_qty":2000,"available_qty":2000,"kit_rate":1,"is_key_material":True},
        {"kit_id":"KIT-005","work_order_id":"WO-2024-003","material_id":"MAT-004","material_category":"包材","required_qty":5000,"available_qty":5000,"kit_rate":1},
    ])

    await session.execute(insert(ForecastStockModel), [
        {"forecast_id":"FC-001","material_id":"MAT-001","material_category":"五金件","forecast_date":date(2024,4,1),"expected_arrival_qty":6000,"expected_arrival_amount":90000,"predicted_fulfillment_rate":0.95,"safety_stock_qty":2000,"current_stock_qty":2500,"supplier_capacity_sufficient":True},
        {"forecast_id":"FC-002","material_id":"MAT-002","material_category":"核心零部件","forecast_date":date(2024,4,1),"expected_arrival_qty":4000,"expected_arrival_amount":160000,"predicted_fulfillment_rate":0.92,"safety_stock_qty":1500,"current_stock_qty":1200,"is_safety_stock_insufficient":True,"supplier_capacity_sufficient":True},
        {"forecast_id":"FC-003","material_id":"MAT-001","material_category":"五金件","forecast_date":date(2024,4,1),"expected_arrival_qty":6000,"expected_arrival_amount":90000,"predicted_delay_risk":True,"safety_stock_qty":1000,"current_stock_qty":300,"is_safety_stock_insufficient":True,"supplier_capacity_sufficient":False},
    ])


async def _seed_ontology(session: AsyncSession) -> None:
    logger.info("Seeding ontology entries...")

    await session.execute(text(
        "INSERT INTO data_asset (datasource_name, table_name, table_comment, tenant_id) VALUES "
        "(:ds1,:tbl1,:cmt1,:tid),(:ds2,:tbl2,:cmt2,:tid),(:ds3,:tbl3,:cmt3,:tid),"
        "(:ds4,:tbl4,:cmt4,:tid),(:ds5,:tbl5,:cmt5,:tid),(:ds6,:tbl6,:cmt6,:tid),"
        "(:ds7,:tbl7,:cmt7,:tid),(:ds8,:tbl8,:cmt8,:tid),(:ds9,:tbl9,:cmt9,:tid),"
        "(:ds10,:tbl10,:cmt10,:tid)"
    ), {
        "ds1":"Default PostgreSQL","tbl1":"purchase_order","cmt1":"采购订单主表","tid":DEFAULT_TENANT_ID,
        "ds2":"Default PostgreSQL","tbl2":"order_material_detail","cmt2":"订单物料明细表","tid":DEFAULT_TENANT_ID,
        "ds3":"Default PostgreSQL","tbl3":"inbound_record","cmt3":"入库记录表","tid":DEFAULT_TENANT_ID,
        "ds4":"Default PostgreSQL","tbl4":"quality_inspection","cmt4":"来料质量检验表","tid":DEFAULT_TENANT_ID,
        "ds5":"Default PostgreSQL","tbl5":"fulfillment_exception","cmt5":"履约异常表","tid":DEFAULT_TENANT_ID,
        "ds6":"Default PostgreSQL","tbl6":"logistics_receipt","cmt6":"物流到货签收表","tid":DEFAULT_TENANT_ID,
        "ds7":"Default PostgreSQL","tbl7":"settlement_reconciliation","cmt7":"对账结算表","tid":DEFAULT_TENANT_ID,
        "ds8":"Default PostgreSQL","tbl8":"supplier_performance","cmt8":"供应商绩效考核表","tid":DEFAULT_TENANT_ID,
        "ds9":"Default PostgreSQL","tbl9":"work_order_kit","cmt9":"生产工单物料齐套表","tid":DEFAULT_TENANT_ID,
        "ds10":"Default PostgreSQL","tbl10":"forecast_stock","cmt10":"备货预测表","tid":DEFAULT_TENANT_ID,
    })

    objects = [
        ("采购订单",'["purchase_order","order_material_detail"]','{"purchase_order":{"1:N":"order_material_detail"}}'),
        ("入库记录",'["inbound_record","purchase_order"]','{"inbound_record":{"N:1":"purchase_order"}}'),
        ("来料质量检验",'["quality_inspection"]',None),
        ("履约异常",'["fulfillment_exception","purchase_order"]',None),
        ("物流签收",'["logistics_receipt","purchase_order"]',None),
        ("对账结算",'["settlement_reconciliation","purchase_order"]',None),
        ("供应商绩效",'["supplier_performance"]',None),
        ("物料齐套检查",'["work_order_kit"]',None),
        ("备货预测",'["forecast_stock"]',None),
    ]
    for i, (name, entities, rels) in enumerate(objects):
        await session.execute(text(
            "INSERT INTO business_object (name, related_entities, entity_relationships, tenant_id) "
            "VALUES (:n, :e, :r, :tid)"
        ), {"n": name, "e": entities, "r": rels, "tid": DEFAULT_TENANT_ID})

    activities = [
        ("采购需求下达",None,"供应商确认接单",None,'["purchase_order"]'),
        ("供应商确认接单","采购需求下达","订单交期确认变更",'["purchase_order"]',None),
        ("订单交期确认变更","供应商确认接单","供应商备货生产",'["purchase_order"]',None),
        ("供应商备货生产","订单交期确认变更","物流发运",'["forecast_stock"]',None),
        ("物流发运","供应商备货生产","到货签收",None,'["logistics_receipt"]'),
        ("到货签收","物流发运","卸货入库",'["logistics_receipt"]',None),
        ("卸货入库","到货签收","来料质量检验",None,'["inbound_record"]'),
        ("来料质量检验","卸货入库","合格入库不合格处理",None,'["quality_inspection"]'),
        ("合格入库不合格处理","来料质量检验","物料齐套检查",'["quality_inspection"]','["inbound_record"]'),
        ("物料齐套检查","合格入库不合格处理","履约异常识别",None,'["work_order_kit"]'),
        ("履约异常识别","物料齐套检查","异常处理闭环",None,'["fulfillment_exception"]'),
        ("异常处理闭环","履约异常识别","供应商绩效考核",'["fulfillment_exception"]',None),
        ("供应商绩效考核","异常处理闭环","对账开票",'["purchase_order","quality_inspection","fulfillment_exception"]','["supplier_performance"]'),
        ("对账开票","供应商绩效考核","付款结算",None,'["settlement_reconciliation"]'),
        ("付款结算","对账开票",None,'["settlement_reconciliation"]',None),
        ("需求预测与备货预判",None,None,'["purchase_order","forecast_stock"]','["forecast_stock"]'),
    ]
    for name, pre, post, inp, out in activities:
        await session.execute(text(
            "INSERT INTO business_activity (name, pre_activities, post_activities, "
            "input_entities, output_entities, tenant_id) "
            "VALUES (:n, :pre, :post, :inp, :out, :tid)"
        ), {"n": name, "pre": pre, "post": post, "inp": inp, "out": out, "tid": DEFAULT_TENANT_ID})


# ════════════════════════════════════════════════════════════════════════════
# Manual Cleanup (CLI only)
# ════════════════════════════════════════════════════════════════════════════

async def clean_sample_data() -> None:
    tables = [
        "forecast_stock","work_order_kit","settlement_reconciliation",
        "logistics_receipt","fulfillment_exception","quality_inspection",
        "inbound_record","order_material_detail","purchase_order",
    ]

    async with async_session_factory() as session:
        for tn in tables:
            await session.execute(text(f"DELETE FROM {tn}"))
        for tn in ["data_asset","activity_entity_rel","activity_metric_rel",
                   "business_rule","metric","business_object_relationship",
                   "business_activity","business_object"]:
            await session.execute(
                text(f"DELETE FROM {tn} WHERE tenant_id = :tid"),
                {"tid": DEFAULT_TENANT_ID},
            )
        await session.commit()
        logger.info("Sample data cleanup complete")


async def reset_and_seed() -> None:
    await clean_sample_data()
    await init_sample_data(force=True)
    logger.info("Reset complete")


if __name__ == "__main__":
    import argparse
    import asyncio

    p = argparse.ArgumentParser(description="Sample data seed management")
    p.add_argument("--reset", action="store_true", help="Clean and re-seed all")
    p.add_argument("--clean", action="store_true", help="Only clean, don't seed")
    args = p.parse_args()

    if args.reset:
        asyncio.run(reset_and_seed())
    elif args.clean:
        asyncio.run(clean_sample_data())
    else:
        asyncio.run(init_sample_data())
