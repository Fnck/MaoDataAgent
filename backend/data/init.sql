-- ============================================================================
-- DataAgent — Database Initialization
--
-- Creates all tables, constraints, and default data from scratch.
-- Designed for fresh database deployment. Safe to re-run (uses IF NOT EXISTS).
-- ============================================================================

BEGIN;

-- ════════════════════════════════════════════════════════════════════════════
-- System Tables
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR NOT NULL UNIQUE,
    password_hash   VARCHAR NOT NULL,
    role            VARCHAR NOT NULL DEFAULT 'user',
    tenant_id       INTEGER
);

CREATE TABLE IF NOT EXISTS tenants (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    created_by_user_id INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_tenant_id;
ALTER TABLE users ADD CONSTRAINT fk_users_tenant_id
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS fk_tenants_created_by_user;
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_created_by_user
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS tenant_members (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
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
    mode            VARCHAR NOT NULL DEFAULT 'dynamic',
    workflow_name   VARCHAR,
    status          VARCHAR NOT NULL DEFAULT 'running',
    final_answer    TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id              SERIAL PRIMARY KEY,
    execution_id    INTEGER NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_index      INTEGER NOT NULL,
    step_type       VARCHAR NOT NULL,
    step_name       VARCHAR NOT NULL,
    input           TEXT,
    output          TEXT,
    status          VARCHAR NOT NULL DEFAULT 'running',
    error           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS debug_events (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    step_id         INTEGER REFERENCES workflow_steps(id) ON DELETE SET NULL,
    category        VARCHAR NOT NULL,
    seq             VARCHAR NOT NULL DEFAULT '0',
    data            TEXT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_datasources (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR NOT NULL,
    dsn             VARCHAR NOT NULL,
    db_type         VARCHAR NOT NULL DEFAULT 'postgres',
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ════════════════════════════════════════════════════════════════════════════
-- Ontology Tables
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS business_object (
    object_id           SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS business_activity (
    activity_id         SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    description         TEXT,
    pre_activities      TEXT,
    post_activities     TEXT,
    operated_objects    TEXT,
    input_entities      TEXT,
    output_entities     TEXT,
    node_metrics        TEXT,
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_rule (
    rule_id             SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    description         TEXT,
    category            VARCHAR(50),
    condition_expression TEXT,
    associated_activity_id INTEGER,
    associated_object_id INTEGER,
    priority            INTEGER,
    status              VARCHAR(20),
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metric (
    metric_id           SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    business_meaning    TEXT,
    calculation_formula TEXT,
    query_logic         TEXT,
    unit                VARCHAR(50),
    data_source         VARCHAR(50),
    refresh_cycle       VARCHAR(50),
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_object_relationship (
    relationship_id     SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    object_id_1         INTEGER NOT NULL,
    object_id_2         INTEGER NOT NULL,
    relationship_type   VARCHAR(50),
    join_logic          TEXT,
    constraint_logic    TEXT,
    join_direction      VARCHAR(10),
    union_logic         TEXT,
    created_by          VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now(),
    updated_by          VARCHAR(50),
    updated_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_metric_rel (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    activity_id         INTEGER NOT NULL,
    metric_id           INTEGER NOT NULL,
    usage_stage         VARCHAR(50),
    created_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_entity_rel (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    activity_id         INTEGER NOT NULL,
    entity_name         VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(10),
    order_index         INTEGER,
    created_time        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_asset (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    datasource_name     VARCHAR(100) NOT NULL,
    table_name          VARCHAR(200) NOT NULL,
    table_comment       TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ════════════════════════════════════════════════════════════════════════════
-- Business Tables
-- ════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS purchase_order (
    order_id                VARCHAR(20) PRIMARY KEY,
    supplier_id             VARCHAR(20) NOT NULL,
    supplier_name           VARCHAR(50) NOT NULL,
    supplier_grade          VARCHAR(10) NOT NULL,
    supplier_type           VARCHAR(20) NOT NULL,
    supplier_region         VARCHAR(20) NOT NULL,
    order_type              VARCHAR(20) NOT NULL,
    order_status            VARCHAR(20) NOT NULL,
    order_date              DATE NOT NULL,
    plan_delivery_date      DATE NOT NULL,
    actual_delivery_date    DATE,
    plan_delivery_qty       NUMERIC(12,2) NOT NULL,
    actual_delivery_qty     NUMERIC(12,2) DEFAULT 0,
    total_amount            NUMERIC(14,2) NOT NULL,
    currency                VARCHAR(10) DEFAULT 'CNY',
    factory                 VARCHAR(50),
    purchaser_id            VARCHAR(20),
    purchaser_name          VARCHAR(30),
    is_fulfillment_ok       BOOLEAN DEFAULT FALSE,
    fulfillment_rate        NUMERIC(5,2),
    on_time_flag            VARCHAR(10),
    overdue_days            INTEGER DEFAULT 0,
    plan_delivery_date_change_count INTEGER DEFAULT 0,
    is_closed               BOOLEAN DEFAULT FALSE,
    close_date              DATE,
    cancel_type             VARCHAR(20),
    create_time             TIMESTAMPTZ DEFAULT now(),
    update_time             TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_material_detail (
    detail_id               VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    material_id             VARCHAR(20) NOT NULL,
    material_name           VARCHAR(80) NOT NULL,
    material_category       VARCHAR(30) NOT NULL,
    is_key_material         BOOLEAN DEFAULT FALSE,
    plan_qty                NUMERIC(12,2) NOT NULL,
    actual_qty              NUMERIC(12,2) DEFAULT 0,
    gap_qty                 NUMERIC(12,2) DEFAULT 0,
    unit_price              NUMERIC(12,4) NOT NULL,
    amount                  NUMERIC(14,2) NOT NULL,
    standard_lead_time_days INTEGER,
    actual_lead_time_days   INTEGER,
    batch_delivery_count    INTEGER DEFAULT 1,
    is_inspection_exempt    BOOLEAN DEFAULT FALSE,
    inspection_type         VARCHAR(10) DEFAULT '全检'
);

CREATE TABLE IF NOT EXISTS inbound_record (
    inbound_id              VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    detail_id               VARCHAR(20) REFERENCES order_material_detail(detail_id),
    material_id             VARCHAR(20) NOT NULL,
    supplier_id             VARCHAR(20) NOT NULL,
    inbound_type            VARCHAR(30) NOT NULL,
    inbound_qty             NUMERIC(12,2) NOT NULL,
    inbound_amount          NUMERIC(14,2) NOT NULL,
    inbound_date            DATE NOT NULL,
    inbound_time_period     VARCHAR(10),
    warehouse_id            VARCHAR(20),
    plan_inbound_qty        NUMERIC(12,2),
    is_rework               BOOLEAN DEFAULT FALSE,
    rework_fulfillment_ok   BOOLEAN
);

CREATE TABLE IF NOT EXISTS quality_inspection (
    inspection_id           VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    detail_id               VARCHAR(20) REFERENCES order_material_detail(detail_id),
    material_id             VARCHAR(20) NOT NULL,
    supplier_id             VARCHAR(20) NOT NULL,
    inspection_date         DATE NOT NULL,
    inspection_result       VARCHAR(10) NOT NULL,
    defect_type             VARCHAR(30),
    defect_qty              NUMERIC(12,2) DEFAULT 0,
    defect_rate             NUMERIC(5,4) DEFAULT 0,
    handle_method           VARCHAR(20),
    is_batch_defect         BOOLEAN DEFAULT FALSE,
    is_new_supplier         BOOLEAN DEFAULT FALSE,
    claim_amount            NUMERIC(14,2) DEFAULT 0,
    is_claim                BOOLEAN DEFAULT FALSE,
    production_stop_hours   NUMERIC(8,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fulfillment_exception (
    exception_id            VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    supplier_id             VARCHAR(20) NOT NULL,
    exception_type          VARCHAR(30) NOT NULL,
    exception_date          DATE NOT NULL,
    exception_desc          VARCHAR(500),
    is_closed               BOOLEAN DEFAULT FALSE,
    close_date              DATE,
    processing_duration_hours NUMERIC(8,2),
    need_manual_intervention BOOLEAN DEFAULT TRUE,
    is_external_factor      BOOLEAN DEFAULT FALSE,
    is_continuous           BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS logistics_receipt (
    receipt_id              VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    logistics_type          VARCHAR(20) NOT NULL,
    shipping_region         VARCHAR(20) NOT NULL,
    plan_arrival_date       DATE NOT NULL,
    actual_arrival_date     DATE,
    is_delayed              BOOLEAN DEFAULT FALSE,
    delay_hours             NUMERIC(8,2) DEFAULT 0,
    unload_overtime         BOOLEAN DEFAULT FALSE,
    inspection_overtime     BOOLEAN DEFAULT FALSE,
    is_rejected             BOOLEAN DEFAULT FALSE,
    is_return_exchange      BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS settlement_reconciliation (
    settlement_id           VARCHAR(20) PRIMARY KEY,
    order_id                VARCHAR(20) NOT NULL REFERENCES purchase_order(order_id),
    supplier_id             VARCHAR(20) NOT NULL,
    settlement_status       VARCHAR(20) NOT NULL,
    invoice_amount          NUMERIC(14,2) DEFAULT 0,
    payment_amount          NUMERIC(14,2) DEFAULT 0,
    payment_date            DATE,
    payment_cycle_days      INTEGER,
    is_payment_held         BOOLEAN DEFAULT FALSE,
    held_amount             NUMERIC(14,2) DEFAULT 0,
    fulfillment_ok          BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS supplier_performance (
    performance_id          VARCHAR(20) PRIMARY KEY,
    supplier_id             VARCHAR(20) NOT NULL,
    supplier_name           VARCHAR(50) NOT NULL,
    period                  VARCHAR(20) NOT NULL,
    comprehensive_score     NUMERIC(5,2),
    delivery_on_time_rate   NUMERIC(5,4),
    quality_pass_rate       NUMERIC(5,4),
    fulfillment_rate        NUMERIC(5,4),
    supplier_grade          VARCHAR(10),
    is_need_interview       BOOLEAN DEFAULT FALSE,
    supply_amount           NUMERIC(14,2) DEFAULT 0,
    total_purchase_amount   NUMERIC(14,2) DEFAULT 0,
    score_change            NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS work_order_kit (
    kit_id                  VARCHAR(20) PRIMARY KEY,
    work_order_id           VARCHAR(20) NOT NULL,
    material_id             VARCHAR(20) NOT NULL,
    material_category       VARCHAR(30) NOT NULL,
    required_qty            NUMERIC(12,2) NOT NULL,
    available_qty           NUMERIC(12,2) NOT NULL,
    kit_rate                NUMERIC(5,4),
    is_key_material         BOOLEAN DEFAULT FALSE,
    is_cause_work_stop      BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS forecast_stock (
    forecast_id             VARCHAR(20) PRIMARY KEY,
    material_id             VARCHAR(20) NOT NULL,
    material_category       VARCHAR(30) NOT NULL,
    forecast_date           DATE NOT NULL,
    expected_arrival_qty    NUMERIC(12,2) DEFAULT 0,
    expected_arrival_amount NUMERIC(14,2) DEFAULT 0,
    predicted_fulfillment_rate NUMERIC(5,4),
    predicted_delay_risk    BOOLEAN DEFAULT FALSE,
    safety_stock_qty        NUMERIC(12,2) DEFAULT 0,
    current_stock_qty       NUMERIC(12,2) DEFAULT 0,
    is_safety_stock_insufficient BOOLEAN DEFAULT FALSE,
    supplier_capacity_sufficient BOOLEAN DEFAULT TRUE,
    demand_forecast_deviation NUMERIC(5,4),
    over_stock_qty          NUMERIC(12,2) DEFAULT 0
);

-- ════════════════════════════════════════════════════════════════════════════
-- Default Data
-- ════════════════════════════════════════════════════════════════════════════

-- Default tenant (id=1)
INSERT INTO tenants (id, name, description, created_by_user_id)
SELECT 1, 'Default', 'Default tenant for localhost PostgreSQL', NULL
WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE name = 'Default');

COMMIT;
