-- ============================================================================
-- DataAgent — PostgreSQL 初始化脚本
-- 由 app/seed/purchase_schema.py 转换而来
--
-- 包含:
--   1. 核心系统表 DDL (users, conversations, messages, debug_events, ...)
--   2. 本体表 DDL (business_object, business_activity, business_rule, metric, ...)
--   3. 业务表 DDL (supplier, material, purchase_order, ...)
--   4. 本体种子数据 (业务对象、业务活动、活动-实体关系、数据资产)
--   5. 示例业务数据 (供应商、物料、库位、采购订单、发货通知、货运单、收货记录、质检单、入库单、退货单、二维码)
--   6. 默认管理员用户
--
-- 用法: psql -U dataagent -d dataagent -f seed_data.sql
-- ============================================================================

BEGIN;

-- ════════════════════════════════════════════════════════════════════════════
-- 1. 核心系统表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR NOT NULL UNIQUE,
    password_hash   VARCHAR NOT NULL,
    role            VARCHAR NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS conversations (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR NOT NULL,
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workflow_executions (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    mode            VARCHAR NOT NULL,                -- 'dynamic' | 'yaml'
    workflow_name   VARCHAR,
    status          VARCHAR NOT NULL DEFAULT 'running', -- 'running' | 'completed' | 'failed'
    final_answer    TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id              SERIAL PRIMARY KEY,
    execution_id    INTEGER NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_index      INTEGER NOT NULL,
    step_type       VARCHAR NOT NULL,                -- 'tool_call' | 'llm_call' | 'condition'
    step_name       VARCHAR NOT NULL,
    input           TEXT,
    output          TEXT,
    status          VARCHAR NOT NULL DEFAULT 'running', -- 'running' | 'completed' | 'failed' | 'skipped'
    error           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS debug_events (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    step_id         INTEGER REFERENCES workflow_steps(id) ON DELETE SET NULL,
    category        VARCHAR NOT NULL,                -- 'llm_call' | 'tool_call' | 'context' | 'system'
    seq             VARCHAR NOT NULL DEFAULT '0',
    data            TEXT,                            -- JSON string
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_datasources (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR NOT NULL,
    dsn             VARCHAR NOT NULL,
    db_type         VARCHAR NOT NULL DEFAULT 'postgres',
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ════════════════════════════════════════════════════════════════════════════
-- 2. 本体表
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS business_activity (
    activity_id     SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    pre_activities  TEXT,
    post_activities TEXT,
    operated_objects TEXT,
    input_entities  TEXT,
    output_entities TEXT,
    node_metrics    TEXT,
    created_by      VARCHAR(50),
    created_time    TIMESTAMPTZ DEFAULT now(),
    updated_by      VARCHAR(50),
    updated_time    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_object (
    object_id           SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    description         TEXT,
    related_entities    TEXT,
    entity_relationships TEXT,
    maintainer          VARCHAR(50),
    department          VARCHAR(50),
    permissions         TEXT,
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_rule (
    rule_id                 SERIAL PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    description             TEXT,
    category                VARCHAR(50),
    condition_expression    TEXT,
    associated_activity_id  INTEGER,
    associated_object_id    INTEGER,
    priority                INTEGER,
    status                  VARCHAR(20),
    created_by              VARCHAR(50),
    created_time            TIMESTAMPTZ DEFAULT now(),
    updated_by              VARCHAR(50),
    updated_time            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metric (
    metric_id           SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    business_meaning    TEXT,
    calculation_formula TEXT,
    query_logic         TEXT,
    unit                VARCHAR(20),
    data_source         VARCHAR(100),
    refresh_cycle       VARCHAR(20),
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_object_relationship (
    relationship_id SERIAL PRIMARY KEY,
    object_id_1     INTEGER NOT NULL,
    object_id_2     INTEGER NOT NULL,
    relationship_type VARCHAR(20),
    join_logic      TEXT,
    constraint_logic TEXT,
    join_direction  VARCHAR(10),
    union_logic     TEXT,
    created_by      VARCHAR(50),
    created_time    TIMESTAMPTZ DEFAULT now(),
    updated_by      VARCHAR(50),
    updated_time    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_metric_rel (
    id          SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    metric_id   INTEGER NOT NULL,
    usage_stage VARCHAR(50),
    created_time TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_entity_rel (
    id          SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(10),              -- 'INPUT' | 'table'
    order_index INTEGER,
    created_time TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_asset (
    id              SERIAL PRIMARY KEY,
    datasource_name VARCHAR(100) NOT NULL,
    table_name      VARCHAR(200) NOT NULL,
    table_comment   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);


-- ════════════════════════════════════════════════════════════════════════════
-- 3. 业务表 (采购入库流程)
-- ════════════════════════════════════════════════════════════════════════════

-- 基础数据
CREATE TABLE IF NOT EXISTS supplier (
    supplier_code   TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    contact         TEXT,
    created_at      TEXT DEFAULT (now()::text)
);

CREATE TABLE IF NOT EXISTS material (
    material_code   TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    spec            TEXT,
    unit            TEXT,
    batch_enabled   BOOLEAN DEFAULT FALSE,
    qr_enabled      BOOLEAN DEFAULT FALSE,
    created_at      TEXT DEFAULT (now()::text)
);

-- 3.1 采购模块
CREATE TABLE IF NOT EXISTS purchase_order (
    po_id       SERIAL PRIMARY KEY,
    dept        TEXT,
    create_time TEXT DEFAULT (now()::text),
    status      TEXT DEFAULT '草稿'
);

CREATE TABLE IF NOT EXISTS purchase_order_line (
    line_id         SERIAL PRIMARY KEY,
    po_id           INTEGER REFERENCES purchase_order(po_id),
    material_code   TEXT,
    planned_qty     REAL,
    received_qty    REAL DEFAULT 0,
    unit_price      REAL,
    expected_date   TEXT
);

-- 3.2 供应商响应与发货
CREATE TABLE IF NOT EXISTS delivery_notice (
    notice_id       SERIAL PRIMARY KEY,
    po_id           INTEGER REFERENCES purchase_order(po_id),
    supplier_code   TEXT,
    expect_ship_time TEXT,
    status          TEXT DEFAULT '新建'
);

CREATE TABLE IF NOT EXISTS delivery_notice_line (
    line_id     SERIAL PRIMARY KEY,
    notice_id   INTEGER REFERENCES delivery_notice(notice_id),
    po_line_id  INTEGER REFERENCES purchase_order_line(line_id),
    material_code TEXT,
    notice_qty  REAL DEFAULT 0,
    shipped_qty REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS freight_order (
    freight_id  SERIAL PRIMARY KEY,
    notice_id   INTEGER REFERENCES delivery_notice(notice_id),
    carrier     TEXT,
    tracking_no TEXT,
    ship_time   TEXT,
    status      TEXT DEFAULT '在途'
);

-- 3.3 收货与质检
CREATE TABLE IF NOT EXISTS receipt_record (
    receipt_id      SERIAL PRIMARY KEY,
    freight_id      INTEGER REFERENCES freight_order(freight_id),
    receiver        TEXT,
    receipt_time    TEXT,
    package_status  TEXT DEFAULT '合格'
);

CREATE TABLE IF NOT EXISTS receipt_record_line (
    line_id     SERIAL PRIMARY KEY,
    receipt_id  INTEGER REFERENCES receipt_record(receipt_id),
    material_code TEXT,
    actual_qty  REAL DEFAULT 0,
    batch_no    TEXT,
    qr_code     TEXT,
    need_qc     BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS qc_order (
    qc_id       SERIAL PRIMARY KEY,
    receipt_id  INTEGER REFERENCES receipt_record(receipt_id),
    qc_user     TEXT,
    qc_time     TEXT,
    overall_result TEXT
);

CREATE TABLE IF NOT EXISTS qc_detail (
    detail_id       SERIAL PRIMARY KEY,
    qc_id           INTEGER REFERENCES qc_order(qc_id),
    material_code   TEXT,
    batch_no        TEXT,
    qr_code         TEXT,
    check_item      TEXT,
    standard_value  TEXT,
    measured_value  TEXT,
    item_result     TEXT,
    final_judgment  TEXT
);

-- 3.4 退货处理
CREATE TABLE IF NOT EXISTS return_order (
    return_id   SERIAL PRIMARY KEY,
    source_type TEXT,
    source_id   INTEGER,
    reason      TEXT,
    total_qty   REAL DEFAULT 0,
    status      TEXT DEFAULT '待退'
);

CREATE TABLE IF NOT EXISTS return_order_line (
    line_id     SERIAL PRIMARY KEY,
    return_id   INTEGER REFERENCES return_order(return_id),
    material_code TEXT,
    batch_no    TEXT,
    qr_code     TEXT,
    return_qty  REAL DEFAULT 0
);

-- 3.5 入库与库位
CREATE TABLE IF NOT EXISTS inbound_order (
    inbound_id       SERIAL PRIMARY KEY,
    qc_id            INTEGER REFERENCES qc_order(qc_id),
    source_receipt_id INTEGER REFERENCES receipt_record(receipt_id),
    inbound_time     TEXT,
    operator         TEXT,
    status           TEXT DEFAULT '暂存'
);

CREATE TABLE IF NOT EXISTS inbound_order_line (
    line_id      SERIAL PRIMARY KEY,
    inbound_id   INTEGER REFERENCES inbound_order(inbound_id),
    material_code TEXT,
    batch_no     TEXT,
    qr_code      TEXT,
    inbound_qty  REAL DEFAULT 0,
    location_code TEXT
);

CREATE TABLE IF NOT EXISTS location (
    location_code TEXT PRIMARY KEY,
    warehouse_id  TEXT,
    zone_type     TEXT,
    capacity      REAL,
    is_occupied   BOOLEAN DEFAULT FALSE
);

-- 3.6 二维码辅助管理
CREATE TABLE IF NOT EXISTS qr_code_master (
    qr_id       SERIAL PRIMARY KEY,
    qr_code     TEXT UNIQUE NOT NULL,
    material_code TEXT,
    batch_no    TEXT,
    generated_by TEXT,
    generate_time TEXT DEFAULT (now()::text),
    source_doc_no TEXT
);


-- ════════════════════════════════════════════════════════════════════════════
-- 4. 默认管理员用户
-- ════════════════════════════════════════════════════════════════════════════
-- 密码: admin123 (bcrypt hash)
INSERT INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$LJ3m4ys3Lg2RqwmMpVr5kuYDFnGMHbOlcEHjPMYVHNwiMbEMwWFWa', 'admin')
ON CONFLICT (username) DO NOTHING;


-- ════════════════════════════════════════════════════════════════════════════
-- 5. 本体种子数据 — 业务对象
-- ════════════════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM business_object LIMIT 1) THEN
        INSERT INTO business_object (name, description, related_entities, entity_relationships, maintainer, department) VALUES
('采购清单',
 '需求方创建的采购凭证，包含采购单头与采购单行，记录采购需求及审批状态',
 '[{"table": "purchase_order", "role": "header"}, {"table": "purchase_order_line", "role": "detail"}]',
 '{"purchase_order": {"1:N": "purchase_order_line"}}',
 NULL, '采购部'),

('采购清单行',
 '采购清单的明细行，记录采购物料、数量、价格及到货要求',
 '[{"table": "purchase_order_line", "role": "detail"}, {"table": "material", "role": "reference"}]',
 '{"purchase_order_line": {"N:1": "purchase_order"}}',
 NULL, '采购部'),

('供应商',
 '提供物料或服务的商业主体，维护供应商主数据信息',
 '[{"table": "supplier", "role": "master"}]',
 NULL,
 '采购部', '采购部'),

('物料',
 '采购和库存管理的基本单元，包含物料编码、名称、规格等主数据',
 '[{"table": "material", "role": "master"}]',
 NULL,
 '仓储部', '仓储部'),

('发货通知单',
 '供应商响应采购清单后创建的发货凭证，包含通知单头与行明细，支持拆分发货',
 '[{"table": "delivery_notice", "role": "header"}, {"table": "delivery_notice_line", "role": "detail"}]',
 '{"delivery_notice": {"N:1": "purchase_order", "1:N": "delivery_notice_line"}}',
 NULL, '供应商'),

('发货通知单行',
 '发货通知单明细，对应采购单行，可拆分通知数量',
 '[{"table": "delivery_notice_line", "role": "detail"}]',
 '{"delivery_notice_line": {"N:1": "delivery_notice", "N:1": "purchase_order_line"}}',
 NULL, '供应商'),

('货运单',
 '实际货物发出时创建的物流凭证，记录承运商、运单号及运输状态',
 '[{"table": "freight_order", "role": "header"}]',
 '{"freight_order": {"N:1": "delivery_notice"}}',
 NULL, '供应商'),

('收货记录',
 '仓库收货员核对实物后创建的收货凭证，包含收货头与行明细，触发质检流程',
 '[{"table": "receipt_record", "role": "header"}, {"table": "receipt_record_line", "role": "detail"}]',
 '{"receipt_record": {"N:1": "freight_order", "1:N": "receipt_record_line", "1:1": "qc_order"}}',
 NULL, '仓储部'),

('收货记录行',
 '按物料/批次明细收货，记录实收数量、批次号和二维码信息',
 '[{"table": "receipt_record_line", "role": "detail"}]',
 '{"receipt_record_line": {"N:1": "receipt_record"}}',
 NULL, '仓储部'),

('质检单',
 '质检部门根据收货记录创建的检验凭证，记录质检头与明细结果',
 '[{"table": "qc_order", "role": "header"}, {"table": "qc_detail", "role": "detail"}]',
 '{"qc_order": {"1:1": "receipt_record", "1:N": "qc_detail"}}',
 NULL, '质检部'),

('质检明细',
 '按物料/批次/二维码逐项检验，记录检验项目、标准值、实测值和最终判定',
 '[{"table": "qc_detail", "role": "detail"}]',
 '{"qc_detail": {"N:1": "qc_order"}}',
 NULL, '质检部'),

('退货单',
 '质检不合格或到货异常时生成的退回凭证，记录退货数量和原因',
 '[{"table": "return_order", "role": "header"}, {"table": "return_order_line", "role": "detail"}]',
 '{"return_order": {"N:1": "qc_order", "1:N": "return_order_line"}}',
 NULL, '仓储部'),

('退货单行',
 '退货单明细，记录退货物料、批次和数量',
 '[{"table": "return_order_line", "role": "detail"}]',
 '{"return_order_line": {"N:1": "return_order"}}',
 NULL, '仓储部'),

('入库单',
 '质检合格后正式入库的凭证，确定物料存放的库位信息',
 '[{"table": "inbound_order", "role": "header"}, {"table": "inbound_order_line", "role": "detail"}]',
 '{"inbound_order": {"1:1": "qc_order", "1:N": "inbound_order_line"}}',
 NULL, '仓储部'),

('入库单行',
 '入库单明细，按物料/批次/二维码入库，指定库位编码',
 '[{"table": "inbound_order_line", "role": "detail"}]',
 '{"inbound_order_line": {"N:1": "inbound_order", "N:1": "location"}}',
 NULL, '仓储部'),

('库位',
 '仓库内物理存储位置的主数据，包含库位编码、库区类型和容量信息',
 '[{"table": "location", "role": "master"}]',
 NULL,
 '仓储部', '仓储部'),

('二维码记录',
 '统一管理货物二维码，记录生成信息及关联单据，支持供应商或仓库生成',
 '[{"table": "qr_code_master", "role": "master"}]',
 NULL,
 '仓储部', '仓储部');

    END IF;
END $$;


-- ════════════════════════════════════════════════════════════════════════════
-- 6. 本体种子数据 — 业务活动
-- ════════════════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM business_activity LIMIT 1) THEN
        INSERT INTO business_activity (name, description, pre_activities, post_activities, input_entities, output_entities, node_metrics) VALUES
('创建采购清单',
 '需求方根据业务需求创建采购清单（单头+单行），填写采购物料、数量、期望到货日期等',
 NULL,
 '供应商创建发货通知',
 NULL,
 '["purchase_order", "purchase_order_line"]',
 '{"key_metrics": ["采购单数", "采购金额", "物料种类数"]}'),

('供应商创建发货通知',
 '供应商响应采购清单，创建发货通知单，可拆分响应采购清单行',
 '创建采购清单',
 '供应商创建货运单',
 '["purchase_order", "purchase_order_line"]',
 '["delivery_notice", "delivery_notice_line"]',
 '{"key_metrics": ["响应率", "交货及时率"]}'),

('供应商创建货运单',
 '供应商实际发货时创建货运单，记录承运商、运单号和发货时间',
 '供应商创建发货通知',
 '仓库收货验收',
 '["delivery_notice", "delivery_notice_line"]',
 '["freight_order"]',
 NULL),

('仓库收货验收',
 '货物到达仓库后，收货员核对实物数量和外包装状态，与货运单比对后创建收货记录，触发质检流程',
 '供应商创建货运单',
 '质检员执行质检',
 '["freight_order"]',
 '["receipt_record", "receipt_record_line"]',
 '{"key_metrics": ["收货及时率", "包装合格率"]}'),

('质检员执行质检',
 '质检员根据收货记录创建质检单，扫描物料批次/二维码逐项检验，判定合格/不合格/让步接收/拒收',
 '仓库收货验收',
 '仓库管理员安排入库, 创建退货单',
 '["receipt_record", "receipt_record_line"]',
 '["qc_order", "qc_detail"]',
 '{"key_metrics": ["合格率", "缺陷率", "质检周期"]}'),

('仓库管理员安排入库',
 '质检合格后，仓库管理员分配库位，创建入库单并执行上架操作',
 '质检员执行质检',
 NULL,
 '["qc_order", "qc_detail", "location"]',
 '["inbound_order", "inbound_order_line"]',
 '{"key_metrics": ["入库及时率", "库位利用率"]}'),

('创建退货单',
 '质检不合格或到货异常时生成退货单，记录退货数量和原因，通知供应商退回处理',
 '质检员执行质检',
 NULL,
 '["qc_order", "qc_detail", "receipt_record"]',
 '["return_order", "return_order_line"]',
 '{"key_metrics": ["退货率", "退货原因分布"]}');

    END IF;
END $$;


-- ════════════════════════════════════════════════════════════════════════════
-- 7. 本体种子数据 — 活动-实体关系 (table)
-- ════════════════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM activity_entity_rel LIMIT 1) THEN

-- 创建采购清单 → purchase_order, purchase_order_line
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'purchase_order', 'table', 0
FROM business_activity a WHERE a.name = '创建采购清单';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'purchase_order_line', 'table', 1
FROM business_activity a WHERE a.name = '创建采购清单';

-- 供应商创建发货通知 → delivery_notice, delivery_notice_line
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'delivery_notice', 'table', 0
FROM business_activity a WHERE a.name = '供应商创建发货通知';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'delivery_notice_line', 'table', 1
FROM business_activity a WHERE a.name = '供应商创建发货通知';

-- 供应商创建货运单 → freight_order
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'freight_order', 'table', 0
FROM business_activity a WHERE a.name = '供应商创建货运单';

-- 仓库收货验收 → receipt_record, receipt_record_line
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'receipt_record', 'table', 0
FROM business_activity a WHERE a.name = '仓库收货验收';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'receipt_record_line', 'table', 1
FROM business_activity a WHERE a.name = '仓库收货验收';

-- 质检员执行质检 → qc_order, qc_detail
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'qc_order', 'table', 0
FROM business_activity a WHERE a.name = '质检员执行质检';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'qc_detail', 'table', 1
FROM business_activity a WHERE a.name = '质检员执行质检';

-- 仓库管理员安排入库 → inbound_order, inbound_order_line
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'inbound_order', 'table', 0
FROM business_activity a WHERE a.name = '仓库管理员安排入库';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'inbound_order_line', 'table', 1
FROM business_activity a WHERE a.name = '仓库管理员安排入库';

-- 创建退货单 → return_order, return_order_line
INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'return_order', 'table', 0
FROM business_activity a WHERE a.name = '创建退货单';

INSERT INTO activity_entity_rel (activity_id, entity_name, entity_type, order_index)
SELECT a.activity_id, 'return_order_line', 'table', 1
FROM business_activity a WHERE a.name = '创建退货单';

    END IF;
END $$;


-- ════════════════════════════════════════════════════════════════════════════
-- 8. 本体种子数据 — 数据资产
-- ════════════════════════════════════════════════════════════════════════════
-- 注意: datasource_name 需要与实际配置一致，默认使用 'default'

INSERT INTO data_asset (datasource_name, table_name, table_comment) VALUES
('default', 'supplier',              '采购入库流程 - supplier'),
('default', 'material',              '采购入库流程 - material'),
('default', 'purchase_order',        '采购入库流程 - purchase_order'),
('default', 'purchase_order_line',   '采购入库流程 - purchase_order_line'),
('default', 'delivery_notice',       '采购入库流程 - delivery_notice'),
('default', 'delivery_notice_line',  '采购入库流程 - delivery_notice_line'),
('default', 'freight_order',         '采购入库流程 - freight_order'),
('default', 'receipt_record',        '采购入库流程 - receipt_record'),
('default', 'receipt_record_line',   '采购入库流程 - receipt_record_line'),
('default', 'qc_order',              '采购入库流程 - qc_order'),
('default', 'qc_detail',             '采购入库流程 - qc_detail'),
('default', 'return_order',          '采购入库流程 - return_order'),
('default', 'return_order_line',     '采购入库流程 - return_order_line'),
('default', 'inbound_order',         '采购入库流程 - inbound_order'),
('default', 'inbound_order_line',    '采购入库流程 - inbound_order_line'),
('default', 'location',              '采购入库流程 - location'),
('default', 'qr_code_master',        '采购入库流程 - qr_code_master')
ON CONFLICT DO NOTHING;


-- ════════════════════════════════════════════════════════════════════════════
-- 9. 示例业务数据
-- ════════════════════════════════════════════════════════════════════════════

-- 幂等检查: 如果已有供应商数据则跳过
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM supplier LIMIT 1) THEN
        RAISE NOTICE '示例数据已存在，跳过插入';
    ELSE
        -- ── 供应商 ──
        INSERT INTO supplier (supplier_code, name, contact) VALUES
        ('SUP001', '深圳华强电子有限公司',   '张经理, 13800010001'),
        ('SUP002', '东莞精密机械有限公司',   '李主管, 13800010002'),
        ('SUP003', '广州包装材料有限公司',   '王工, 13800010003');

        -- ── 物料 ──
        INSERT INTO material (material_code, name, spec, unit, batch_enabled, qr_enabled) VALUES
        ('MAT001', '电子元器件A',  'SOP-8封装',           '个', TRUE,  FALSE),
        ('MAT002', '精密螺丝M3',   'M3×12',               '盒', TRUE,  TRUE),
        ('MAT003', '包装纸箱',     '600×400×300mm',       '个', FALSE, FALSE),
        ('MAT004', '电路板PCB',    '双面板 100×80mm',     '块', TRUE,  TRUE);

        -- ── 库位 ──
        INSERT INTO location (location_code, warehouse_id, zone_type, capacity) VALUES
        ('A-01-01', 'WH-A', '托盘存储区',   500.0),
        ('A-01-02', 'WH-A', '托盘存储区',   500.0),
        ('A-02-01', 'WH-A', '周转箱区',     200.0),
        ('A-02-02', 'WH-A', '周转箱区',     200.0),
        ('B-01-01', 'WH-B', '待检区',       100.0),
        ('B-01-02', 'WH-B', '退货暂存区',    50.0);

        -- ── 采购订单 #1 (已完成) ──
        INSERT INTO purchase_order (dept, status) VALUES ('生产部', '已完成');

        INSERT INTO purchase_order_line (po_id, material_code, planned_qty, received_qty, unit_price, expected_date) VALUES
        (1, 'MAT001', 1000.0, 1000.0, 2.50,  '2026-05-15'),
        (1, 'MAT004',  500.0,  500.0, 45.00, '2026-05-15');

        -- ── 采购订单 #2 (部分收货) ──
        INSERT INTO purchase_order (dept, status) VALUES ('仓储部', '部分收货');

        INSERT INTO purchase_order_line (po_id, material_code, planned_qty, received_qty, unit_price, expected_date) VALUES
        (2, 'MAT002', 200.0, 200.0, 1.80, '2026-06-20'),
        (2, 'MAT003', 500.0, 300.0, 0.50, '2026-06-20');

        -- ── 发货通知单 #1 (PO#1, 已发货) ──
        INSERT INTO delivery_notice (po_id, supplier_code, expect_ship_time, status) VALUES
        (1, 'SUP001', '2026-05-12', '已发货');

        INSERT INTO delivery_notice_line (notice_id, po_line_id, material_code, notice_qty, shipped_qty) VALUES
        (1, 1, 'MAT001', 1000.0, 1000.0),
        (1, 2, 'MAT004',  500.0,  500.0);

        -- ── 发货通知单 #2 (PO#2, 供应商已确认) ──
        INSERT INTO delivery_notice (po_id, supplier_code, expect_ship_time, status) VALUES
        (2, 'SUP002', '2026-06-18', '已确认');

        INSERT INTO delivery_notice_line (notice_id, po_line_id, material_code, notice_qty, shipped_qty) VALUES
        (2, 3, 'MAT002', 200.0, 200.0),
        (2, 4, 'MAT003', 500.0, 300.0);

        -- ── 货运单 #1 (DN#1, 已签收) ──
        INSERT INTO freight_order (notice_id, carrier, tracking_no, ship_time, status) VALUES
        (1, '顺丰速运', 'SF1234567890', '2026-05-12T10:00:00', '已签收');

        -- ── 货运单 #2 (DN#2, 在途) ──
        INSERT INTO freight_order (notice_id, carrier, tracking_no, ship_time, status) VALUES
        (2, '德邦物流', 'DB9876543210', '2026-06-18T14:00:00', '在途');

        -- ── 收货记录 #1 (FO#1) ──
        INSERT INTO receipt_record (freight_id, receiver, receipt_time, package_status) VALUES
        (1, '仓库管理员-赵', '2026-05-14T09:30:00', '合格');

        INSERT INTO receipt_record_line (receipt_id, material_code, actual_qty, batch_no, qr_code, need_qc) VALUES
        (1, 'MAT001', 1000.0, 'BATCH-20260514-001', NULL,           FALSE),
        (1, 'MAT004',  500.0, 'BATCH-20260514-002', 'QR-PCB-001',   TRUE);

        -- ── 质检单 (收货记录 #1) ──
        INSERT INTO qc_order (receipt_id, qc_user, qc_time, overall_result) VALUES
        (1, '质检员-钱', '2026-05-14T14:00:00', '合格');

        INSERT INTO qc_detail (qc_id, material_code, batch_no, qr_code, check_item, standard_value, measured_value, item_result, final_judgment) VALUES
        (1, 'MAT004', 'BATCH-20260514-002', 'QR-PCB-001', '外观检查', '无划痕、无起泡', '表面无异常', '合格', '通过'),
        (1, 'MAT004', 'BATCH-20260514-002', 'QR-PCB-001', '电气测试', '导通电阻<0.1Ω', '0.03Ω',       '合格', '通过');

        -- ── 收货记录 #2 (FO#2, 部分收货) ──
        INSERT INTO receipt_record (freight_id, receiver, receipt_time, package_status) VALUES
        (2, '仓库管理员-赵', '2026-06-19T10:00:00', '合格');

        INSERT INTO receipt_record_line (receipt_id, material_code, actual_qty, batch_no, qr_code, need_qc) VALUES
        (2, 'MAT002', 200.0, 'BATCH-20260619-001', 'QR-SCREW-002', FALSE),
        (2, 'MAT003', 300.0, NULL,                 NULL,           FALSE);

        -- ── 入库单 #1 (质检 #1, 全部合格) ──
        INSERT INTO inbound_order (qc_id, source_receipt_id, inbound_time, operator, status) VALUES
        (1, 1, '2026-05-14T16:00:00', '仓库管理员-孙', '已完成');

        INSERT INTO inbound_order_line (inbound_id, material_code, batch_no, qr_code, inbound_qty, location_code) VALUES
        (1, 'MAT001', 'BATCH-20260514-001', NULL,           1000.0, 'A-01-01'),
        (1, 'MAT004', 'BATCH-20260514-002', 'QR-PCB-001',    500.0, 'A-02-01');

        -- ── 入库单 #2 (收货记录 #2, 部分入库) ──
        INSERT INTO inbound_order (qc_id, source_receipt_id, inbound_time, operator, status) VALUES
        (NULL, 2, '2026-06-19T14:00:00', '仓库管理员-孙', '暂存');

        INSERT INTO inbound_order_line (inbound_id, material_code, batch_no, qr_code, inbound_qty, location_code) VALUES
        (2, 'MAT002', 'BATCH-20260619-001', 'QR-SCREW-002', 200.0, 'A-02-02'),
        (2, 'MAT003', NULL,                 NULL,            300.0, 'A-01-02');

        -- ── 二维码记录 ──
        INSERT INTO qr_code_master (qr_code, material_code, batch_no, generated_by, source_doc_no) VALUES
        ('QR-PCB-001',   'MAT004', 'BATCH-20260514-002', '采购员-周', 'PO-1'),
        ('QR-SCREW-002', 'MAT002', 'BATCH-20260619-001', '采购员-周', 'PO-2');

        -- ── 退货单 (入库 #1, MAT001 部分不良) ──
        INSERT INTO return_order (source_type, source_id, reason, total_qty, status) VALUES
        ('receipt_record', 1, '外包装破损,10个电子元器件引脚弯曲', 10.0, '已退');

        INSERT INTO return_order_line (return_id, material_code, batch_no, qr_code, return_qty) VALUES
        (1, 'MAT001', 'BATCH-20260514-001', NULL, 10.0);

        RAISE NOTICE '示例数据插入完成';
    END IF;
END $$;


COMMIT;
