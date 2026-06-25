-- ============================================================================
-- DataAgent — 制造业供应商订单履约场景 示例数据
--
-- 基于《智能问数业务分析-数据表与流程规则梳理》文档
-- 10张业务表 + 完整示例数据
--
-- 用法: psql -U dataagent -d dataagent -f sample_manufacturing.sql
-- ============================================================================

BEGIN;

-- ════════════════════════════════════════════════════════════════════════════
-- 1. 采购订单主表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS purchase_order (
    order_id                    VARCHAR(20) PRIMARY KEY,
    supplier_id                 VARCHAR(20) NOT NULL,
    supplier_name               VARCHAR(50) NOT NULL,
    supplier_grade              VARCHAR(10) NOT NULL,       -- A/B/C/淘汰
    supplier_type               VARCHAR(20) NOT NULL,       -- 战略/备选
    supplier_region             VARCHAR(20) NOT NULL,       -- 本地/异地
    order_type                  VARCHAR(20) NOT NULL,       -- 常规/紧急/备货/框架协议
    order_status                VARCHAR(20) NOT NULL,       -- 未发货/部分到货/全部到货/已关闭/已取消
    order_date                  DATE NOT NULL,
    plan_delivery_date          DATE NOT NULL,
    actual_delivery_date        DATE,
    plan_delivery_qty           DECIMAL(12,2) NOT NULL,
    actual_delivery_qty         DECIMAL(12,2) DEFAULT 0,
    total_amount                DECIMAL(14,2) NOT NULL,
    currency                    VARCHAR(10) DEFAULT 'CNY',
    factory                     VARCHAR(50),
    purchaser_id                VARCHAR(20),
    purchaser_name              VARCHAR(30),
    is_fulfillment_ok           BOOLEAN DEFAULT FALSE,
    fulfillment_rate            DECIMAL(5,2),
    on_time_flag                VARCHAR(10),                -- 提前/准时/逾期
    overdue_days                INT DEFAULT 0,
    plan_delivery_date_change_count INT DEFAULT 0,
    is_closed                   BOOLEAN DEFAULT FALSE,
    close_date                  DATE,
    cancel_type                 VARCHAR(20),
    create_time                 TIMESTAMPTZ DEFAULT now(),
    update_time                 TIMESTAMPTZ DEFAULT now()
);

-- ════════════════════════════════════════════════════════════════════════════
-- 2. 订单物料明细表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS order_material_detail (
    detail_id                   VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    material_id                 VARCHAR(20) NOT NULL,
    material_name               VARCHAR(80) NOT NULL,
    material_category           VARCHAR(30) NOT NULL,       -- 原材料/包材/五金件/核心零部件/通用辅料/外协加工件
    is_key_material             BOOLEAN DEFAULT FALSE,
    plan_qty                    DECIMAL(12,2) NOT NULL,
    actual_qty                  DECIMAL(12,2) DEFAULT 0,
    gap_qty                     DECIMAL(12,2) DEFAULT 0,
    unit_price                  DECIMAL(12,4) NOT NULL,
    amount                      DECIMAL(14,2) NOT NULL,
    standard_lead_time_days     INT,
    actual_lead_time_days       INT,
    batch_delivery_count        INT DEFAULT 1,
    is_inspection_exempt        BOOLEAN DEFAULT FALSE,
    inspection_type             VARCHAR(10) DEFAULT '全检'  -- 免检/全检/抽检
);

-- ════════════════════════════════════════════════════════════════════════════
-- 3. 入库记录表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS inbound_record (
    inbound_id                  VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    detail_id                   VARCHAR(20) REFERENCES order_material_detail(detail_id),
    material_id                 VARCHAR(20) NOT NULL,
    supplier_id                 VARCHAR(20) NOT NULL,
    inbound_type                VARCHAR(30) NOT NULL,       -- 正常入库/退货返工入库
    inbound_qty                 DECIMAL(12,2) NOT NULL,
    inbound_amount              DECIMAL(14,2) NOT NULL,
    inbound_date                DATE NOT NULL,
    inbound_time_period         VARCHAR(10),                -- 白天/夜间
    warehouse_id                VARCHAR(20),
    plan_inbound_qty            DECIMAL(12,2),
    is_rework                   BOOLEAN DEFAULT FALSE,
    rework_fulfillment_ok       BOOLEAN
);

-- ════════════════════════════════════════════════════════════════════════════
-- 4. 来料质量检验表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS quality_inspection (
    inspection_id               VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    detail_id                   VARCHAR(20) REFERENCES order_material_detail(detail_id),
    material_id                 VARCHAR(20) NOT NULL,
    supplier_id                 VARCHAR(20) NOT NULL,
    inspection_date             DATE NOT NULL,
    inspection_result           VARCHAR(10) NOT NULL,       -- 合格/不合格
    defect_type                 VARCHAR(30),                -- 尺寸偏差/外观缺陷/性能不合格
    defect_qty                  DECIMAL(12,2) DEFAULT 0,
    defect_rate                 DECIMAL(5,4) DEFAULT 0,
    handle_method               VARCHAR(20),                -- 退货/返工/特采放行
    is_batch_defect             BOOLEAN DEFAULT FALSE,
    is_new_supplier             BOOLEAN DEFAULT FALSE,
    claim_amount                DECIMAL(14,2) DEFAULT 0,
    is_claim                    BOOLEAN DEFAULT FALSE,
    production_stop_hours       DECIMAL(8,2) DEFAULT 0
);

-- ════════════════════════════════════════════════════════════════════════════
-- 5. 履约异常表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fulfillment_exception (
    exception_id                VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    supplier_id                 VARCHAR(20) NOT NULL,
    exception_type              VARCHAR(30) NOT NULL,       -- 交期延误/数量短装/质量不良/物流破损/订单变更未同步/物流堵车/仓库爆仓/物料涨价暂缓交货
    exception_date              DATE NOT NULL,
    exception_desc              VARCHAR(500),
    is_closed                   BOOLEAN DEFAULT FALSE,
    close_date                  DATE,
    processing_duration_hours   DECIMAL(8,2),
    need_manual_intervention    BOOLEAN DEFAULT TRUE,
    is_external_factor          BOOLEAN DEFAULT FALSE,
    is_continuous               BOOLEAN DEFAULT FALSE
);

-- ════════════════════════════════════════════════════════════════════════════
-- 6. 物流到货签收表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS logistics_receipt (
    receipt_id                  VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    logistics_type              VARCHAR(20) NOT NULL,       -- 快递/整车/零担
    shipping_region             VARCHAR(20) NOT NULL,       -- 本地/省外/跨境
    plan_arrival_date           DATE NOT NULL,
    actual_arrival_date         DATE,
    is_delayed                  BOOLEAN DEFAULT FALSE,
    delay_hours                 DECIMAL(8,2) DEFAULT 0,
    unload_overtime             BOOLEAN DEFAULT FALSE,
    inspection_overtime         BOOLEAN DEFAULT FALSE,
    is_rejected                 BOOLEAN DEFAULT FALSE,
    is_return_exchange          BOOLEAN DEFAULT FALSE
);

-- ════════════════════════════════════════════════════════════════════════════
-- 7. 对账结算表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS settlement_reconciliation (
    settlement_id               VARCHAR(20) PRIMARY KEY,
    order_id                    VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    supplier_id                 VARCHAR(20) NOT NULL,
    settlement_status           VARCHAR(20) NOT NULL,       -- 未对账/已对账未开票/已开票/已付款
    invoice_amount              DECIMAL(14,2) DEFAULT 0,
    payment_amount              DECIMAL(14,2) DEFAULT 0,
    payment_date                DATE,
    payment_cycle_days          INT,
    is_payment_held             BOOLEAN DEFAULT FALSE,
    held_amount                 DECIMAL(14,2) DEFAULT 0,
    fulfillment_ok              BOOLEAN DEFAULT FALSE
);

-- ════════════════════════════════════════════════════════════════════════════
-- 8. 供应商绩效考核表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS supplier_performance (
    performance_id              VARCHAR(20) PRIMARY KEY,
    supplier_id                 VARCHAR(20) NOT NULL,
    supplier_name               VARCHAR(50) NOT NULL,
    period                      VARCHAR(20) NOT NULL,       -- 年/月/季度 e.g. "2024-Q1"
    comprehensive_score         DECIMAL(5,2),
    delivery_on_time_rate       DECIMAL(5,4),
    quality_pass_rate           DECIMAL(5,4),
    fulfillment_rate            DECIMAL(5,4),
    supplier_grade              VARCHAR(10),
    is_need_interview           BOOLEAN DEFAULT FALSE,
    supply_amount               DECIMAL(14,2) DEFAULT 0,
    total_purchase_amount       DECIMAL(14,2) DEFAULT 0,
    score_change                DECIMAL(5,2)
);

-- ════════════════════════════════════════════════════════════════════════════
-- 9. 生产工单物料齐套表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS work_order_kit (
    kit_id                      VARCHAR(20) PRIMARY KEY,
    work_order_id               VARCHAR(20) NOT NULL,
    material_id                 VARCHAR(20) NOT NULL,
    material_category           VARCHAR(30) NOT NULL,
    required_qty                DECIMAL(12,2) NOT NULL,
    available_qty               DECIMAL(12,2) NOT NULL,
    kit_rate                    DECIMAL(5,4),
    is_key_material             BOOLEAN DEFAULT FALSE,
    is_cause_work_stop          BOOLEAN DEFAULT FALSE
);

-- ════════════════════════════════════════════════════════════════════════════
-- 10. 备货预测表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS forecast_stock (
    forecast_id                 VARCHAR(20) PRIMARY KEY,
    material_id                 VARCHAR(20) NOT NULL,
    material_category           VARCHAR(30) NOT NULL,
    forecast_date               DATE NOT NULL,
    expected_arrival_qty        DECIMAL(12,2) DEFAULT 0,
    expected_arrival_amount     DECIMAL(14,2) DEFAULT 0,
    predicted_fulfillment_rate  DECIMAL(5,4),
    predicted_delay_risk        BOOLEAN DEFAULT FALSE,
    safety_stock_qty            DECIMAL(12,2) DEFAULT 0,
    current_stock_qty           DECIMAL(12,2) DEFAULT 0,
    is_safety_stock_insufficient BOOLEAN DEFAULT FALSE,
    supplier_capacity_sufficient BOOLEAN DEFAULT TRUE,
    demand_forecast_deviation   DECIMAL(5,4),
    over_stock_qty              DECIMAL(12,2) DEFAULT 0
);


-- ════════════════════════════════════════════════════════════════════════════
-- 示例数据
-- ════════════════════════════════════════════════════════════════════════════

-- 采购订单
INSERT INTO purchase_order (order_id, supplier_id, supplier_name, supplier_grade, supplier_type, supplier_region, order_type, order_status, order_date, plan_delivery_date, actual_delivery_date, plan_delivery_qty, actual_delivery_qty, total_amount, factory, purchaser_id, purchaser_name, is_fulfillment_ok, fulfillment_rate, on_time_flag, overdue_days, is_closed)
VALUES
('PO-2024-001', 'SUP001', '苏州精密五金有限公司', 'A', '战略', '本地', '常规', '全部到货', '2024-01-05', '2024-01-20', '2024-01-19', 5000, 5000, 125000.00, '一分厂', 'P001', '张三', TRUE, 100.00, '准时', 0, TRUE),
('PO-2024-002', 'SUP001', '苏州精密五金有限公司', 'A', '战略', '本地', '紧急', '全部到货', '2024-01-10', '2024-01-15', '2024-01-16', 2000, 2000, 58000.00, '二分厂', 'P002', '李四', TRUE, 95.00, '逾期', 1, TRUE),
('PO-2024-003', 'SUP002', '深圳鸿达电子有限公司', 'B', '备选', '本地', '常规', '部分到货', '2024-02-01', '2024-02-15', NULL, 10000, 7000, 300000.00, '一分厂', 'P001', '张三', FALSE, 70.00, NULL, 0, FALSE),
('PO-2024-004', 'SUP003', '东莞华丰包材有限公司', 'B', '备选', '异地', '常规', '全部到货', '2024-02-05', '2024-02-25', '2024-02-22', 3000, 3000, 45000.00, '二分厂', 'P003', '王五', TRUE, 100.00, '提前', 0, TRUE),
('PO-2024-005', 'SUP001', '苏州精密五金有限公司', 'A', '战略', '本地', '备货', '全部到货', '2024-03-01', '2024-03-20', '2024-03-18', 8000, 8000, 200000.00, '一分厂', 'P001', '张三', TRUE, 100.00, '提前', 0, TRUE),
('PO-2024-006', 'SUP002', '深圳鸿达电子有限公司', 'B', '备选', '本地', '紧急', '未发货', '2024-03-10', '2024-03-20', NULL, 4000, 0, 120000.00, '二分厂', 'P002', '李四', FALSE, NULL, NULL, 0, FALSE),
('PO-2024-007', 'SUP003', '东莞华丰包材有限公司', 'B', '备选', '异地', '常规', '已关闭', '2024-03-15', '2024-04-01', NULL, 5000, 5000, 75000.00, '一分厂', 'P003', '王五', FALSE, NULL, NULL, 0, TRUE);

-- 订单物料明细
INSERT INTO order_material_detail (detail_id, order_id, material_id, material_name, material_category, is_key_material, plan_qty, actual_qty, gap_qty, unit_price, amount, standard_lead_time_days, actual_lead_time_days, batch_delivery_count, is_inspection_exempt, inspection_type)
VALUES
('DET-001', 'PO-2024-001', 'MAT-001', 'M4不锈钢螺栓', '五金件', TRUE, 3000, 3000, 0, 15.00, 45000.00, 7, 7, 1, FALSE, '抽检'),
('DET-002', 'PO-2024-001', 'MAT-002', 'PCB电路板V2', '核心零部件', TRUE, 2000, 2000, 0, 40.00, 80000.00, 14, 14, 1, FALSE, '全检'),
('DET-003', 'PO-2024-002', 'MAT-003', '散热铝型材', '原材料', FALSE, 2000, 2000, 0, 29.00, 58000.00, 10, 11, 1, TRUE, '免检'),
('DET-004', 'PO-2024-003', 'MAT-001', 'M4不锈钢螺栓', '五金件', TRUE, 6000, 4000, 2000, 15.00, 90000.00, 7, NULL, 2, FALSE, '抽检'),
('DET-005', 'PO-2024-003', 'MAT-004', 'PE包装袋', '包材', FALSE, 4000, 3000, 1000, 5.00, 20000.00, 3, NULL, 2, TRUE, '免检'),
('DET-006', 'PO-2024-004', 'MAT-004', 'PE包装袋', '包材', FALSE, 3000, 3000, 0, 5.00, 15000.00, 3, 3, 1, TRUE, '免检'),
('DET-007', 'PO-2024-005', 'MAT-001', 'M4不锈钢螺栓', '五金件', TRUE, 5000, 5000, 0, 15.00, 75000.00, 7, 6, 1, FALSE, '抽检'),
('DET-008', 'PO-2024-005', 'MAT-002', 'PCB电路板V2', '核心零部件', TRUE, 3000, 3000, 0, 40.00, 120000.00, 14, 13, 1, FALSE, '全检'),
('DET-009', 'PO-2024-006', 'MAT-002', 'PCB电路板V2', '核心零部件', TRUE, 4000, 0, 4000, 30.00, 120000.00, 14, NULL, 0, FALSE, '全检');

-- 入库记录
INSERT INTO inbound_record (inbound_id, order_id, detail_id, material_id, supplier_id, inbound_type, inbound_qty, inbound_amount, inbound_date, warehouse_id, plan_inbound_qty)
VALUES
('IN-001', 'PO-2024-001', 'DET-001', 'MAT-001', 'SUP001', '正常入库', 3000, 45000.00, '2024-01-19', 'WH-A01', 3000),
('IN-002', 'PO-2024-001', 'DET-002', 'MAT-002', 'SUP001', '正常入库', 2000, 80000.00, '2024-01-19', 'WH-A02', 2000),
('IN-003', 'PO-2024-002', 'DET-003', 'MAT-003', 'SUP001', '正常入库', 2000, 58000.00, '2024-01-16', 'WH-B01', 2000),
('IN-004', 'PO-2024-003', 'DET-004', 'MAT-001', 'SUP002', '正常入库', 4000, 60000.00, '2024-02-20', 'WH-A01', 4000),
('IN-005', 'PO-2024-004', 'DET-006', 'MAT-004', 'SUP003', '正常入库', 3000, 15000.00, '2024-02-22', 'WH-B02', 3000),
('IN-006', 'PO-2024-005', 'DET-007', 'MAT-001', 'SUP001', '正常入库', 5000, 75000.00, '2024-03-18', 'WH-A01', 5000),
('IN-007', 'PO-2024-005', 'DET-008', 'MAT-002', 'SUP001', '正常入库', 3000, 120000.00, '2024-03-18', 'WH-A02', 3000);

-- 来料质量检验
INSERT INTO quality_inspection (inspection_id, order_id, detail_id, material_id, supplier_id, inspection_date, inspection_result, defect_type, defect_qty, defect_rate, handle_method, is_batch_defect, is_new_supplier)
VALUES
('QC-001', 'PO-2024-001', 'DET-001', 'MAT-001', 'SUP001', '2024-01-19', '合格', NULL, 0, 0.0000, NULL, FALSE, FALSE),
('QC-002', 'PO-2024-001', 'DET-002', 'MAT-002', 'SUP001', '2024-01-19', '合格', NULL, 0, 0.0000, NULL, FALSE, FALSE),
('QC-003', 'PO-2024-002', 'DET-003', 'MAT-003', 'SUP001', '2024-01-16', '合格', NULL, 0, 0.0000, NULL, FALSE, FALSE),
('QC-004', 'PO-2024-003', 'DET-004', 'MAT-001', 'SUP002', '2024-02-20', '不合格', '尺寸偏差', 200, 0.0500, '返工', FALSE, TRUE),
('QC-005', 'PO-2024-004', 'DET-006', 'MAT-004', 'SUP003', '2024-02-22', '合格', NULL, 0, 0.0000, NULL, FALSE, FALSE),
('QC-006', 'PO-2024-005', 'DET-007', 'MAT-001', 'SUP001', '2024-03-18', '合格', NULL, 0, 0.0000, NULL, FALSE, FALSE),
('QC-007', 'PO-2024-005', 'DET-008', 'MAT-002', 'SUP001', '2024-03-18', '不合格', '外观缺陷', 50, 0.0167, '特采放行', FALSE, FALSE);

-- 履约异常
INSERT INTO fulfillment_exception (exception_id, order_id, supplier_id, exception_type, exception_date, exception_desc, is_closed, close_date, processing_duration_hours, need_manual_intervention, is_external_factor, is_continuous)
VALUES
('EX-001', 'PO-2024-002', 'SUP001', '交期延误', '2024-01-16', '受物流堵车影响，延迟1天到货', TRUE, '2024-01-17', 24.0, TRUE, TRUE, FALSE),
('EX-002', 'PO-2024-003', 'SUP002', '数量短装', '2024-02-15', '计划10000件，实到7000件，缺3000件', FALSE, NULL, NULL, TRUE, FALSE, TRUE),
('EX-003', 'PO-2024-003', 'SUP002', '质量不良', '2024-02-20', '来料检验发现尺寸偏差，不良率5%', FALSE, NULL, NULL, TRUE, FALSE, FALSE),
('EX-004', 'PO-2024-005', 'SUP001', '质量不良', '2024-03-18', '外观缺陷，不良率1.67%', TRUE, '2024-03-19', 4.0, FALSE, FALSE, FALSE);

-- 物流到货签收
INSERT INTO logistics_receipt (receipt_id, order_id, logistics_type, shipping_region, plan_arrival_date, actual_arrival_date, is_delayed, delay_hours)
VALUES
('LOG-001', 'PO-2024-001', '整车', '本地', '2024-01-19', '2024-01-19', FALSE, 0),
('LOG-002', 'PO-2024-002', '快递', '本地', '2024-01-15', '2024-01-16', TRUE, 24),
('LOG-003', 'PO-2024-003', '整车', '本地', '2024-02-15', '2024-02-20', TRUE, 120),
('LOG-004', 'PO-2024-004', '零担', '省外', '2024-02-22', '2024-02-22', FALSE, 0),
('LOG-005', 'PO-2024-005', '整车', '本地', '2024-03-18', '2024-03-18', FALSE, 0);

-- 对账结算
INSERT INTO settlement_reconciliation (settlement_id, order_id, supplier_id, settlement_status, invoice_amount, payment_amount, payment_date, payment_cycle_days, is_payment_held, fulfillment_ok)
VALUES
('STL-001', 'PO-2024-001', 'SUP001', '已付款', 125000.00, 125000.00, '2024-02-20', 30, FALSE, TRUE),
('STL-002', 'PO-2024-002', 'SUP001', '已付款', 58000.00, 58000.00, '2024-02-15', 30, FALSE, TRUE),
('STL-003', 'PO-2024-003', 'SUP002', '已对账未开票', 300000.00, 0, NULL, 0, TRUE, FALSE),
('STL-004', 'PO-2024-004', 'SUP003', '已开票', 45000.00, 45000.00, '2024-03-25', 30, FALSE, TRUE),
('STL-005', 'PO-2024-005', 'SUP001', '已付款', 200000.00, 200000.00, '2024-04-18', 30, FALSE, TRUE);

-- 供应商绩效考核 (2024-Q1)
INSERT INTO supplier_performance (performance_id, supplier_id, supplier_name, period, comprehensive_score, delivery_on_time_rate, quality_pass_rate, fulfillment_rate, supplier_grade, is_need_interview, supply_amount, total_purchase_amount, score_change)
VALUES
('PERF-001', 'SUP001', '苏州精密五金有限公司', '2024-Q1', 92.5, 0.9500, 0.9800, 0.9800, 'A', FALSE, 383000.00, 383000.00, 1.5),
('PERF-002', 'SUP002', '深圳鸿达电子有限公司', '2024-Q1', 68.0, 0.5000, 0.8000, 0.7000, 'C', TRUE, 210000.00, 420000.00, -3.0),
('PERF-003', 'SUP003', '东莞华丰包材有限公司', '2024-Q1', 88.0, 1.0000, 1.0000, 1.0000, 'B', FALSE, 60000.00, 120000.00, 2.0);

-- 生产工单物料齐套
INSERT INTO work_order_kit (kit_id, work_order_id, material_id, material_category, required_qty, available_qty, kit_rate, is_key_material, is_cause_work_stop)
VALUES
('KIT-001', 'WO-2024-001', 'MAT-001', '五金件', 2000, 2000, 1.0000, TRUE, FALSE),
('KIT-002', 'WO-2024-001', 'MAT-002', '核心零部件', 1500, 1500, 1.0000, TRUE, FALSE),
('KIT-003', 'WO-2024-002', 'MAT-001', '五金件', 3000, 1000, 0.3333, TRUE, TRUE),
('KIT-004', 'WO-2024-002', 'MAT-002', '核心零部件', 2000, 2000, 1.0000, TRUE, FALSE),
('KIT-005', 'WO-2024-003', 'MAT-004', '包材', 5000, 5000, 1.0000, FALSE, FALSE);

-- 备货预测
INSERT INTO forecast_stock (forecast_id, material_id, material_category, forecast_date, expected_arrival_qty, expected_arrival_amount, predicted_fulfillment_rate, predicted_delay_risk, safety_stock_qty, current_stock_qty, is_safety_stock_insufficient, supplier_capacity_sufficient)
VALUES
('FC-001', 'MAT-001', '五金件', '2024-04-01', 6000, 90000.00, 0.9500, FALSE, 2000, 2500, FALSE, TRUE),
('FC-002', 'MAT-002', '核心零部件', '2024-04-01', 4000, 160000.00, 0.9200, FALSE, 1500, 1200, TRUE, TRUE),
('FC-003', 'MAT-001', '五金件', '2024-04-01', 6000, 90000.00, NULL, TRUE, 1000, 300, TRUE, FALSE);


-- ════════════════════════════════════════════════════════════════════════════
-- 本体数据 (Business Ontology)
-- ════════════════════════════════════════════════════════════════════════════

-- 业务对象 (Business Objects) - 新表
INSERT INTO business_object (name, description, related_entities, entity_relationships, maintainer, department)
VALUES
('采购订单', '制造业供应商订单履约核心单据，记录采购需求、供应商、交期、履约状态等信息',
 '["purchase_order", "order_material_detail"]',
 '{"purchase_order": {"1:N": "order_material_detail"}}',
 '供应链管理部', '采购中心'),

('入库记录', '货物到货后的入库操作记录，关联订单和物料',
 '["inbound_record", "purchase_order"]',
 '{"inbound_record": {"N:1": "purchase_order"}}',
 '仓储管理部', '仓库'),

('来料质量检验', 'IQC对来料的质量检验结果记录',
 '["quality_inspection", "order_material_detail"]',
 '{"quality_inspection": {"N:1": "order_material_detail"}}',
 '质量管理部', 'QC'),

('履约异常', '供应商订单履约过程中的异常事件记录',
 '["fulfillment_exception", "purchase_order"]',
 '{"fulfillment_exception": {"N:1": "purchase_order"}}',
 '供应链管理部', '运营中心'),

('物流签收', '货物物流运输和到货签收记录',
 '["logistics_receipt", "purchase_order"]',
 '{"logistics_receipt": {"N:1": "purchase_order"}}',
 '物流管理部', '仓储'),

('对账结算', '采购对账、开票和付款结算记录',
 '["settlement_reconciliation", "purchase_order"]',
 '{"settlement_reconciliation": {"N:1": "purchase_order"}}',
 '财务管理部', '应付'),

('供应商绩效', '供应商月度/季度履约绩效考核结果',
 '["supplier_performance"]',
 NULL,
 '供应链管理部', '采购中心'),

('物料齐套检查', '生产工单所需物料的齐套状态检查',
 '["work_order_kit"]',
 NULL,
 '生产管理部', 'PMC'),

('备货预测', '基于历史数据的物料到货预测和安全库存预警',
 '["forecast_stock"]',
 NULL,
 '供应链管理部', '计划中心')
ON CONFLICT DO NOTHING;

-- 业务活动 (Business Activities) - 基于文档 N1-N17
INSERT INTO business_activity (name, description, pre_activities, post_activities, input_entities, output_entities, node_metrics)
VALUES
('采购需求下达',
 '采购部门根据生产计划下达采购订单',
 NULL,
 '供应商确认接单',
 '["purchase_order"]',
 '["purchase_order"]',
 '{"key_metrics": ["采购单数", "采购金额"]}'),

('供应商确认接单',
 '供应商确认订单并反馈交期',
 '采购需求下达',
 '订单交期确认变更',
 '["purchase_order"]',
 NULL,
 NULL),

('订单交期确认变更',
 '确认计划交货日期，或因需求变化变更交期',
 '供应商确认接单',
 '供应商备货生产',
 '["purchase_order"]',
 NULL,
 '{"key_metrics": ["交期变更次数"]}'),

('供应商备货生产',
 '供应商按订单要求组织生产备货',
 '订单交期确认变更',
 '物流发运',
 '["forecast_stock"]',
 NULL,
 '{"key_metrics": ["备货产能充足率"]}'),

('物流发运',
 '供应商发货，选择物流方式',
 '供应商备货生产',
 '到货签收',
 NULL,
 '["logistics_receipt"]',
 '{"key_metrics": ["物流准时率"]}'),

('到货签收',
 '货物到达仓库，签收确认',
 '物流发运',
 '卸货入库',
 '["logistics_receipt"]',
 NULL,
 '{"key_metrics": ["签收及时率"]}'),

('卸货入库',
 '仓库卸货、入库操作',
 '到货签收',
 '来料质量检验',
 NULL,
 '["inbound_record"]',
 '{"key_metrics": ["入库及时率"]}'),

('来料质量检验',
 'IQC对来料进行质量检验',
 '卸货入库',
 '合格入库不合格处理',
 NULL,
 '["quality_inspection"]',
 '{"key_metrics": ["合格率", "不良率"]}'),

('合格入库不合格处理',
 '合格物料入库，不合格物料退货/返工/特采',
 '来料质量检验',
 '物料齐套检查',
 '["quality_inspection"]',
 '["inbound_record"]',
 '{"key_metrics": ["退货率", "返工率"]}'),

('物料齐套检查',
 '检查生产工单所需物料是否齐套',
 '合格入库不合格处理',
 '履约异常识别',
 NULL,
 '["work_order_kit"]',
 '{"key_metrics": ["齐套率", "缺料品类数"]}'),

('履约异常识别',
 '识别交期延误、短装、质量不良等异常',
 '物料齐套检查',
 '异常处理闭环',
 NULL,
 '["fulfillment_exception"]',
 '{"key_metrics": ["异常发生数", "异常原因分布"]}'),

('异常处理闭环',
 '人工介入处理异常并闭环',
 '履约异常识别',
 NULL,
 '["fulfillment_exception"]',
 NULL,
 '{"key_metrics": ["异常闭环率", "平均处理时长"]}'),

('供应商绩效考核',
 '定期对供应商进行履约评分和分级',
 '异常处理闭环',
 '对账开票',
 '["purchase_order", "quality_inspection", "fulfillment_exception"]',
 '["supplier_performance"]',
 '{"key_metrics": ["综合评分", "A级供应商数"]}'),

('对账开票',
 '采购与供应商对账并开具发票',
 '供应商绩效考核',
 '付款结算',
 NULL,
 '["settlement_reconciliation"]',
 '{"key_metrics": ["对账完成率"]}'),

('付款结算',
 '按合同约定付款',
 '对账开票',
 NULL,
 '["settlement_reconciliation"]',
 NULL,
 '{"key_metrics": ["应付金额", "暂缓付款金额"]}'),

('需求预测与备货预判',
 '基于历史数据预测未来履约情况',
 NULL,
 NULL,
 '["purchase_order", "forecast_stock"]',
 '["forecast_stock"]',
 '{"key_metrics": ["预测履约率", "延误风险物料数"]}')
ON CONFLICT DO NOTHING;

-- 数据资产 (Data Assets) - 注册新表到数据资产目录
INSERT INTO data_asset (datasource_name, table_name, table_comment) VALUES
('default', 'purchase_order',            '采购订单主表 - 包含供应商、交期、履约、金额等核心字段'),
('default', 'order_material_detail',     '订单物料明细表 - 物料品类、数量、单价、交期信息'),
('default', 'inbound_record',            '入库记录表 - 仓库入库操作、入库数量、库位信息'),
('default', 'quality_inspection',        '来料质量检验表 - IQC检验结果、不良类型、处理方式'),
('default', 'fulfillment_exception',     '履约异常表 - 交期延误、短装、质量不良等异常跟踪'),
('default', 'logistics_receipt',         '物流到货签收表 - 物流方式、到货时间、延迟信息'),
('default', 'settlement_reconciliation', '对账结算表 - 发票、付款、暂缓付款信息'),
('default', 'supplier_performance',      '供应商绩效考核表 - 综合评分、等级、供货金额'),
('default', 'work_order_kit',            '生产工单物料齐套表 - 齐套率、缺料、停工影响'),
('default', 'forecast_stock',            '备货预测表 - 到货预测、安全库存、延误风险')
ON CONFLICT DO NOTHING;

COMMIT;
