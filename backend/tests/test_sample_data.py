"""
Unit tests for manufacturing supplier order fulfillment sample data.

Validates:
- 10 business tables exist with correct schema
- Sample data integrity (foreign keys, business rules)
- Key business metrics (fulfillment rate, on-time delivery, quality pass rate)
- Cross-table query scenarios
"""

import pytest
import pytest_asyncio
from sqlalchemy import text


TABLES = [
    "purchase_order", "order_material_detail", "inbound_record",
    "quality_inspection", "fulfillment_exception", "logistics_receipt",
    "settlement_reconciliation", "supplier_performance",
    "work_order_kit", "forecast_stock",
]

SAMPLE_DATA = [
    # purchase_order (7 rows)
    "INSERT INTO purchase_order VALUES ('PO-2024-001','SUP001','苏州精密五金有限公司','A','战略','本地','常规','全部到货','2024-01-05','2024-01-20','2024-01-19',5000,5000,125000,'CNY','一分厂','P001','张三',1,100,'准时',0,0,1,NULL,NULL,'2024-01-01','2024-01-01')",
    "INSERT INTO purchase_order VALUES ('PO-2024-002','SUP001','苏州精密五金有限公司','A','战略','本地','紧急','全部到货','2024-01-10','2024-01-15','2024-01-16',2000,2000,58000,'CNY','二分厂','P002','李四',1,95,'逾期',1,0,1,NULL,NULL,'2024-01-01','2024-01-01')",
    "INSERT INTO purchase_order VALUES ('PO-2024-003','SUP002','深圳鸿达电子有限公司','B','备选','本地','常规','部分到货','2024-02-01','2024-02-15',NULL,10000,7000,300000,'CNY','一分厂','P001','张三',0,70,NULL,0,0,0,NULL,NULL,'2024-02-01','2024-02-01')",
    "INSERT INTO purchase_order VALUES ('PO-2024-004','SUP003','东莞华丰包材有限公司','B','备选','异地','常规','全部到货','2024-02-05','2024-02-25','2024-02-22',3000,3000,45000,'CNY','二分厂','P003','王五',1,100,'提前',0,0,1,NULL,NULL,'2024-02-05','2024-02-05')",
    "INSERT INTO purchase_order VALUES ('PO-2024-005','SUP001','苏州精密五金有限公司','A','战略','本地','备货','全部到货','2024-03-01','2024-03-20','2024-03-18',8000,8000,200000,'CNY','一分厂','P001','张三',1,100,'提前',0,0,1,NULL,NULL,'2024-03-01','2024-03-01')",
    "INSERT INTO purchase_order VALUES ('PO-2024-006','SUP002','深圳鸿达电子有限公司','B','备选','本地','紧急','未发货','2024-03-10','2024-03-20',NULL,4000,0,120000,'CNY','二分厂','P002','李四',0,NULL,NULL,0,0,0,NULL,NULL,'2024-03-10','2024-03-10')",
    "INSERT INTO purchase_order VALUES ('PO-2024-007','SUP003','东莞华丰包材有限公司','B','备选','异地','常规','已关闭','2024-03-15','2024-04-01',NULL,5000,5000,75000,'CNY','一分厂','P003','王五',0,NULL,NULL,0,0,1,NULL,NULL,'2024-03-15','2024-03-15')",
    # order_material_detail (9 rows)
    "INSERT INTO order_material_detail VALUES ('DET-001','PO-2024-001','MAT-001','M4不锈钢螺栓','五金件',1,3000,3000,0,15,45000,7,7,1,0,'抽检')",
    "INSERT INTO order_material_detail VALUES ('DET-002','PO-2024-001','MAT-002','PCB电路板V2','核心零部件',1,2000,2000,0,40,80000,14,14,1,0,'全检')",
    "INSERT INTO order_material_detail VALUES ('DET-003','PO-2024-002','MAT-003','散热铝型材','原材料',0,2000,2000,0,29,58000,10,11,1,1,'免检')",
    "INSERT INTO order_material_detail VALUES ('DET-004','PO-2024-003','MAT-001','M4不锈钢螺栓','五金件',1,6000,4000,2000,15,90000,7,NULL,2,0,'抽检')",
    "INSERT INTO order_material_detail VALUES ('DET-005','PO-2024-003','MAT-004','PE包装袋','包材',0,4000,3000,1000,5,20000,3,NULL,2,1,'免检')",
    "INSERT INTO order_material_detail VALUES ('DET-006','PO-2024-004','MAT-004','PE包装袋','包材',0,3000,3000,0,5,15000,3,3,1,1,'免检')",
    "INSERT INTO order_material_detail VALUES ('DET-007','PO-2024-005','MAT-001','M4不锈钢螺栓','五金件',1,5000,5000,0,15,75000,7,6,1,0,'抽检')",
    "INSERT INTO order_material_detail VALUES ('DET-008','PO-2024-005','MAT-002','PCB电路板V2','核心零部件',1,3000,3000,0,40,120000,14,13,1,0,'全检')",
    "INSERT INTO order_material_detail VALUES ('DET-009','PO-2024-006','MAT-002','PCB电路板V2','核心零部件',1,4000,0,4000,30,120000,14,NULL,0,0,'全检')",
    # inbound_record (7 rows)
    "INSERT INTO inbound_record VALUES ('IN-001','PO-2024-001','DET-001','MAT-001','SUP001','正常入库',3000,45000,'2024-01-19',NULL,'WH-A01',3000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-002','PO-2024-001','DET-002','MAT-002','SUP001','正常入库',2000,80000,'2024-01-19',NULL,'WH-A02',2000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-003','PO-2024-002','DET-003','MAT-003','SUP001','正常入库',2000,58000,'2024-01-16',NULL,'WH-B01',2000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-004','PO-2024-003','DET-004','MAT-001','SUP002','正常入库',4000,60000,'2024-02-20',NULL,'WH-A01',4000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-005','PO-2024-004','DET-006','MAT-004','SUP003','正常入库',3000,15000,'2024-02-22',NULL,'WH-B02',3000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-006','PO-2024-005','DET-007','MAT-001','SUP001','正常入库',5000,75000,'2024-03-18',NULL,'WH-A01',5000,0,NULL)",
    "INSERT INTO inbound_record VALUES ('IN-007','PO-2024-005','DET-008','MAT-002','SUP001','正常入库',3000,120000,'2024-03-18',NULL,'WH-A02',3000,0,NULL)",
    # quality_inspection (7 rows)
    "INSERT INTO quality_inspection VALUES ('QC-001','PO-2024-001','DET-001','MAT-001','SUP001','2024-01-19','合格',NULL,0,0,NULL,0,0,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-002','PO-2024-001','DET-002','MAT-002','SUP001','2024-01-19','合格',NULL,0,0,NULL,0,0,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-003','PO-2024-002','DET-003','MAT-003','SUP001','2024-01-16','合格',NULL,0,0,NULL,0,0,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-004','PO-2024-003','DET-004','MAT-001','SUP002','2024-02-20','不合格','尺寸偏差',200,0.05,'返工',0,1,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-005','PO-2024-004','DET-006','MAT-004','SUP003','2024-02-22','合格',NULL,0,0,NULL,0,0,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-006','PO-2024-005','DET-007','MAT-001','SUP001','2024-03-18','合格',NULL,0,0,NULL,0,0,0,0,0)",
    "INSERT INTO quality_inspection VALUES ('QC-007','PO-2024-005','DET-008','MAT-002','SUP001','2024-03-18','不合格','外观缺陷',50,0.0167,'特采放行',0,0,0,0,0)",
    # fulfillment_exception (4 rows)
    "INSERT INTO fulfillment_exception VALUES ('EX-001','PO-2024-002','SUP001','交期延误','2024-01-16','受物流堵车影响',1,'2024-01-17',24,1,1,0)",
    "INSERT INTO fulfillment_exception VALUES ('EX-002','PO-2024-003','SUP002','数量短装','2024-02-15','计划10000实到7000',0,NULL,NULL,1,0,1)",
    "INSERT INTO fulfillment_exception VALUES ('EX-003','PO-2024-003','SUP002','质量不良','2024-02-20','尺寸偏差不良率5%',0,NULL,NULL,1,0,0)",
    "INSERT INTO fulfillment_exception VALUES ('EX-004','PO-2024-005','SUP001','质量不良','2024-03-18','外观缺陷不良率1.67%',1,'2024-03-19',4,0,0,0)",
    # logistics_receipt (5 rows)
    "INSERT INTO logistics_receipt VALUES ('LOG-001','PO-2024-001','整车','本地','2024-01-19','2024-01-19',0,0,0,0,0,0)",
    "INSERT INTO logistics_receipt VALUES ('LOG-002','PO-2024-002','快递','本地','2024-01-15','2024-01-16',1,24,0,0,0,0)",
    "INSERT INTO logistics_receipt VALUES ('LOG-003','PO-2024-003','整车','本地','2024-02-15','2024-02-20',1,120,0,0,0,0)",
    "INSERT INTO logistics_receipt VALUES ('LOG-004','PO-2024-004','零担','省外','2024-02-22','2024-02-22',0,0,0,0,0,0)",
    "INSERT INTO logistics_receipt VALUES ('LOG-005','PO-2024-005','整车','本地','2024-03-18','2024-03-18',0,0,0,0,0,0)",
    # settlement_reconciliation (5 rows)
    "INSERT INTO settlement_reconciliation VALUES ('STL-001','PO-2024-001','SUP001','已付款',125000,125000,'2024-02-20',30,0,0,1)",
    "INSERT INTO settlement_reconciliation VALUES ('STL-002','PO-2024-002','SUP001','已付款',58000,58000,'2024-02-15',30,0,0,1)",
    "INSERT INTO settlement_reconciliation VALUES ('STL-003','PO-2024-003','SUP002','已对账未开票',300000,0,NULL,0,1,0,0)",
    "INSERT INTO settlement_reconciliation VALUES ('STL-004','PO-2024-004','SUP003','已开票',45000,45000,'2024-03-25',30,0,0,1)",
    "INSERT INTO settlement_reconciliation VALUES ('STL-005','PO-2024-005','SUP001','已付款',200000,200000,'2024-04-18',30,0,0,1)",
    # supplier_performance (3 rows)
    "INSERT INTO supplier_performance VALUES ('PERF-001','SUP001','苏州精密五金有限公司','2024-Q1',92.5,0.95,0.98,0.98,'A',0,383000,383000,1.5)",
    "INSERT INTO supplier_performance VALUES ('PERF-002','SUP002','深圳鸿达电子有限公司','2024-Q1',68,0.5,0.8,0.7,'C',1,210000,420000,-3)",
    "INSERT INTO supplier_performance VALUES ('PERF-003','SUP003','东莞华丰包材有限公司','2024-Q1',88,1,1,1,'B',0,60000,120000,2)",
    # work_order_kit (5 rows)
    "INSERT INTO work_order_kit VALUES ('KIT-001','WO-2024-001','MAT-001','五金件',2000,2000,1,1,0)",
    "INSERT INTO work_order_kit VALUES ('KIT-002','WO-2024-001','MAT-002','核心零部件',1500,1500,1,1,0)",
    "INSERT INTO work_order_kit VALUES ('KIT-003','WO-2024-002','MAT-001','五金件',3000,1000,0.3333,1,1)",
    "INSERT INTO work_order_kit VALUES ('KIT-004','WO-2024-002','MAT-002','核心零部件',2000,2000,1,1,0)",
    "INSERT INTO work_order_kit VALUES ('KIT-005','WO-2024-003','MAT-004','包材',5000,5000,1,0,0)",
    # forecast_stock (3 rows)
    "INSERT INTO forecast_stock VALUES ('FC-001','MAT-001','五金件','2024-04-01',6000,90000,0.95,0,2000,2500,0,1,NULL,0)",
    "INSERT INTO forecast_stock VALUES ('FC-002','MAT-002','核心零部件','2024-04-01',4000,160000,0.92,0,1500,1200,1,1,NULL,0)",
    "INSERT INTO forecast_stock VALUES ('FC-003','MAT-001','五金件','2024-04-01',6000,90000,NULL,1,1000,300,1,0,NULL,0)",
]


@pytest_asyncio.fixture
async def seeded_db(db_session):
    """Seed the sample data into the test database and return the session."""
    # Create a test tenant first (required by ontology FK)
    await db_session.execute(text(
        "INSERT INTO tenants (id, name, description) VALUES (1, 'Default', 'Test tenant')"
    ))

    # Seed business tables
    for stmt in SAMPLE_DATA:
        await db_session.execute(text(stmt))

    # Seed ontology: business objects for new tables (with tenant_id)
    ontology_objects = [
        ("采购订单", '["purchase_order","order_material_detail"]', '{"purchase_order":{"1:N":"order_material_detail"}}'),
        ("入库记录", '["inbound_record","purchase_order"]', '{"inbound_record":{"N:1":"purchase_order"}}'),
        ("来料质量检验", '["quality_inspection"]', None),
        ("履约异常", '["fulfillment_exception","purchase_order"]', None),
        ("物流签收", '["logistics_receipt","purchase_order"]', None),
        ("对账结算", '["settlement_reconciliation","purchase_order"]', None),
        ("供应商绩效", '["supplier_performance"]', None),
        ("物料齐套检查", '["work_order_kit"]', None),
        ("备货预测", '["forecast_stock"]', None),
    ]
    for name, entities, rels in ontology_objects:
        await db_session.execute(text(
            "INSERT INTO business_object (name, related_entities, entity_relationships, tenant_id) VALUES (:n, :e, :r, 1)"
        ), {"n": name, "e": entities, "r": rels})

    # Seed ontology: business activities
    activities_data = [
        ("采购需求下达", '["purchase_order"]'),
        ("供应商确认接单", '["purchase_order"]'),
        ("来料质量检验", '["quality_inspection"]'),
        ("履约异常识别", '["fulfillment_exception"]'),
        ("供应商绩效考核", '["purchase_order","quality_inspection","supplier_performance"]'),
    ]
    for name, entities in activities_data:
        await db_session.execute(text(
            "INSERT INTO business_activity (name, output_entities, tenant_id) VALUES (:n, :e, 1)"
        ), {"n": name, "e": entities})

    # Seed data assets
    new_tables = [
        "purchase_order", "order_material_detail", "inbound_record",
        "quality_inspection", "fulfillment_exception", "logistics_receipt",
        "settlement_reconciliation", "supplier_performance",
        "work_order_kit", "forecast_stock",
    ]
    for table_name in new_tables:
        await db_session.execute(text(
            "INSERT INTO data_asset (datasource_name, table_name, table_comment, tenant_id) VALUES ('default', :t, :c, 1)"
        ), {"t": table_name, "c": f"Sample data - {table_name}"})

    await db_session.commit()
    return db_session


# ══════════════════════════════════════════════════════════
# Schema & Data Integrity Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_all_tables_exist(seeded_db):
    for table_name in TABLES:
        result = await seeded_db.execute(
            text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        )
        assert result.fetchone() is not None, f"Table '{table_name}' should exist"


@pytest.mark.asyncio
async def test_purchase_order_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM purchase_order"))
    assert result.scalar() == 7


@pytest.mark.asyncio
async def test_purchase_order_status_distribution(seeded_db):
    result = await seeded_db.execute(
        text("SELECT order_status, COUNT(*) FROM purchase_order GROUP BY order_status")
    )
    statuses = {row[0]: row[1] for row in result.fetchall()}
    assert statuses.get("全部到货") == 4
    assert statuses.get("部分到货") == 1
    assert statuses.get("未发货") == 1
    assert statuses.get("已关闭") == 1


@pytest.mark.asyncio
async def test_material_detail_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM order_material_detail"))
    assert result.scalar() == 9


@pytest.mark.asyncio
async def test_material_categories(seeded_db):
    result = await seeded_db.execute(
        text("SELECT DISTINCT material_category FROM order_material_detail ORDER BY material_category")
    )
    categories = [row[0] for row in result.fetchall()]
    for cat in ["五金件", "核心零部件", "原材料", "包材"]:
        assert cat in categories


@pytest.mark.asyncio
async def test_inbound_record_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM inbound_record"))
    assert result.scalar() == 7


@pytest.mark.asyncio
async def test_quality_inspection_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM quality_inspection"))
    assert result.scalar() == 7


@pytest.mark.asyncio
async def test_quality_results(seeded_db):
    result = await seeded_db.execute(
        text("SELECT inspection_result, COUNT(*) FROM quality_inspection GROUP BY inspection_result")
    )
    results = {row[0]: row[1] for row in result.fetchall()}
    assert results.get("合格", 0) >= 5
    assert results.get("不合格", 0) >= 2


@pytest.mark.asyncio
async def test_fulfillment_exceptions(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM fulfillment_exception"))
    assert result.scalar() == 4


@pytest.mark.asyncio
async def test_exception_types(seeded_db):
    result = await seeded_db.execute(text("SELECT DISTINCT exception_type FROM fulfillment_exception"))
    types = {row[0] for row in result.fetchall()}
    assert {"交期延误", "数量短装", "质量不良"}.issubset(types)


@pytest.mark.asyncio
async def test_logistics_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM logistics_receipt"))
    assert result.scalar() == 5


@pytest.mark.asyncio
async def test_logistics_delays(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM logistics_receipt WHERE is_delayed = 1"))
    assert result.scalar() >= 2


@pytest.mark.asyncio
async def test_settlement_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM settlement_reconciliation"))
    assert result.scalar() == 5


@pytest.mark.asyncio
async def test_settlement_held(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM settlement_reconciliation WHERE is_payment_held = 1"))
    assert result.scalar() >= 1


@pytest.mark.asyncio
async def test_supplier_performance_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM supplier_performance"))
    assert result.scalar() == 3


@pytest.mark.asyncio
async def test_supplier_grades(seeded_db):
    result = await seeded_db.execute(text("SELECT DISTINCT supplier_grade FROM supplier_performance"))
    grades = {row[0] for row in result.fetchall()}
    assert {"A", "B", "C"}.issubset(grades)


@pytest.mark.asyncio
async def test_work_order_kit_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM work_order_kit"))
    assert result.scalar() == 5


@pytest.mark.asyncio
async def test_kit_cause_work_stop(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM work_order_kit WHERE is_cause_work_stop = 1"))
    assert result.scalar() >= 1


@pytest.mark.asyncio
async def test_forecast_count(seeded_db):
    result = await seeded_db.execute(text("SELECT COUNT(*) FROM forecast_stock"))
    assert result.scalar() == 3


@pytest.mark.asyncio
async def test_forecast_risks(seeded_db):
    result = await seeded_db.execute(
        text("SELECT COUNT(*) FROM forecast_stock WHERE predicted_delay_risk = 1 OR is_safety_stock_insufficient = 1")
    )
    assert result.scalar() >= 2


# ══════════════════════════════════════════════════════════
# Business Rule Validation Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fulfillment_rate_calculation(seeded_db):
    """R1-01: fulfillment rate = fulfilled / total valid orders"""
    result = await seeded_db.execute(text("""
        SELECT SUM(CASE WHEN is_fulfillment_ok = 1 THEN 1 ELSE 0 END) as fulfilled,
               COUNT(*) as total
        FROM purchase_order
    """))
    row = result.fetchone()
    assert row[0] >= 4
    assert row[1] == 7


@pytest.mark.asyncio
async def test_on_time_delivery(seeded_db):
    """R2-01: on-time delivery rate"""
    result = await seeded_db.execute(text("""
        SELECT on_time_flag, COUNT(*) FROM purchase_order
        WHERE on_time_flag IS NOT NULL GROUP BY on_time_flag
    """))
    flags = {row[0]: row[1] for row in result.fetchall()}
    assert "准时" in flags
    assert "提前" in flags
    assert "逾期" in flags


@pytest.mark.asyncio
async def test_supplier_score_grading(seeded_db):
    """R6-02: A≥90, B=75-89, C=60-74"""
    result = await seeded_db.execute(
        text("SELECT supplier_id, supplier_grade, comprehensive_score FROM supplier_performance")
    )
    for row in result.fetchall():
        sid, grade, score = row[0], row[1], float(row[2]) if row[2] else 0
        if grade == "A":
            assert score >= 90, f"{sid}: A should have score >= 90, got {score}"
        elif grade == "B":
            assert 75 <= score <= 89, f"{sid}: B should be 75-89, got {score}"
        elif grade == "C":
            assert 60 <= score <= 74, f"{sid}: C should be 60-74, got {score}"


@pytest.mark.asyncio
async def test_cross_table_order_fulfillment(seeded_db):
    """Cross-table: verify order lifecycle across purchase/logistics/inspection/exception."""
    result = await seeded_db.execute(text("""
        SELECT po.order_id, po.is_fulfillment_ok, lr.is_delayed,
               (SELECT COUNT(*) FROM quality_inspection qi WHERE qi.order_id = po.order_id AND qi.inspection_result = '不合格') as failed_qc,
               (SELECT COUNT(*) FROM fulfillment_exception fe WHERE fe.order_id = po.order_id AND fe.is_closed = 0) as open_exceptions
        FROM purchase_order po
        LEFT JOIN logistics_receipt lr ON lr.order_id = po.order_id
        WHERE po.order_status NOT IN ('已取消')
        ORDER BY po.order_id
    """))
    orders = result.fetchall()
    assert len(orders) >= 5

    po_001 = next((r for r in orders if r[0] == "PO-2024-001"), None)
    assert po_001 and po_001[1] == 1

    po_003 = next((r for r in orders if r[0] == "PO-2024-003"), None)
    assert po_003 and po_003[4] >= 1


@pytest.mark.asyncio
async def test_work_order_kit_calculation(seeded_db):
    """R3-01: kit rate = available / required"""
    result = await seeded_db.execute(text("""
        SELECT SUM(CASE WHEN kit_rate >= 1.0 THEN 1 ELSE 0 END) as fully_kitted,
               SUM(CASE WHEN is_cause_work_stop = 1 THEN 1 ELSE 0 END) as stopped
        FROM work_order_kit
    """))
    row = result.fetchone()
    assert row[0] >= 3
    assert row[1] >= 1


@pytest.mark.asyncio
async def test_forecast_stock_alerts(seeded_db):
    """R8-01/02: verify forecast alerts for insufficient safety stock"""
    result = await seeded_db.execute(text("""
        SELECT material_id, current_stock_qty, safety_stock_qty
        FROM forecast_stock
        WHERE current_stock_qty < safety_stock_qty
    """))
    alerts = result.fetchall()
    assert len(alerts) >= 1


# ══════════════════════════════════════════════════════════
# Ontology / Data Asset Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_data_assets_cover_new_tables(seeded_db):
    """Verify all 10 new sample tables have data_asset entries."""
    new_tables = [
        "purchase_order", "order_material_detail", "inbound_record",
        "quality_inspection", "fulfillment_exception", "logistics_receipt",
        "settlement_reconciliation", "supplier_performance",
        "work_order_kit", "forecast_stock",
    ]
    result = await seeded_db.execute(
        text("SELECT table_name FROM data_asset WHERE datasource_name = 'default'")
    )
    registered = {row[0] for row in result.fetchall()}
    for table_name in new_tables:
        assert table_name in registered, f"Table '{table_name}' should be in data_asset"


@pytest.mark.asyncio
async def test_business_objects_for_new_tables(seeded_db):
    """Verify business objects exist for the new sample tables."""
    expected_objects = [
        "采购订单", "入库记录", "来料质量检验", "履约异常",
        "物流签收", "对账结算", "供应商绩效", "物料齐套检查", "备货预测",
    ]
    result = await seeded_db.execute(
        text("SELECT name FROM business_object ORDER BY name")
    )
    names = {row[0] for row in result.fetchall()}
    for obj_name in expected_objects:
        assert obj_name in names, f"Business object '{obj_name}' should exist"


@pytest.mark.asyncio
async def test_business_activities_for_document_flow(seeded_db):
    """Verify core business activities from the document are registered."""
    required_activities = [
        "采购需求下达", "供应商确认接单",
        "来料质量检验", "履约异常识别", "供应商绩效考核",
    ]
    result = await seeded_db.execute(
        text("SELECT name FROM business_activity ORDER BY name")
    )
    names = {row[0] for row in result.fetchall()}
    for activity_name in required_activities:
        assert activity_name in names, f"Activity '{activity_name}' should exist"
