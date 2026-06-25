// ── Auth ───────────────────────────────────────────────

export interface User {
  id: number;
  username: string;
  role: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

// ── Conversations ──────────────────────────────────────

export interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// ── Chat ───────────────────────────────────────────────

export interface ChatContext {
  selected_files: string[];
  selected_tables: string[];
}

export interface ChatRequest {
  message: string;
  conversation_id: number;
  context?: ChatContext;
}

export type DebugCategory = "llm_call" | "tool_call" | "context" | "system";

export type SSEEvent =
  | { type: "chunk"; content: string }
  | { type: "end"; message_id: number }
  | { type: "error"; error: string }
  | { type: "step_start"; step_id: number; step_name: string; step_type: string }
  | { type: "step_end"; step_id: number; output: string | null }
  | { type: "step_error"; step_id: number; error: string }
  | {
      type: "debug";
      event_id: number;
      category: DebugCategory;
      data: Record<string, unknown>;
      timestamp: string;
      seq?: number;
      step_id?: number;
      message_id?: number;
    };

// ── Workflow ───────────────────────────────────────────

export interface WorkflowStep {
  step_id: number;
  step_name: string;
  step_type: string;
  status: "running" | "completed" | "failed";
  output: string | null;
  error: string | null;
}

// ── Storage ────────────────────────────────────────────

export interface StorageItem {
  key: string;
  size: number;
  last_modified: string | null;
  is_dir: boolean;
}

// ── Datasource ─────────────────────────────────────────

export interface TableInfo {
  datasource_name: string;
  table_name: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  comment: string | null;
}

// ── Ontology ───────────────────────────────────────────

export interface BusinessActivity {
  activity_id: number;
  name: string;
  description: string | null;
  pre_activities: string | null;
  post_activities: string | null;
  operated_objects: string | null;
  input_entities: string | null;
  output_entities: string | null;
  node_metrics: string | null;
  created_by: string | null;
  created_time: string | null;
  updated_by: string | null;
  updated_time: string | null;
}

export interface BusinessObject {
  object_id: number;
  name: string;
  description: string | null;
  related_entities: string | null;
  entity_relationships: string | null;
  maintainer: string | null;
  department: string | null;
  permissions: string | null;
  created_by: string | null;
  created_time: string | null;
  updated_by: string | null;
  updated_time: string | null;
}

export interface BusinessRule {
  rule_id: number;
  name: string;
  description: string | null;
  category: string | null;
  condition_expression: string | null;
  associated_activity_id: number | null;
  associated_object_id: number | null;
  priority: number | null;
  status: string | null;
  created_by: string | null;
  created_time: string | null;
  updated_by: string | null;
  updated_time: string | null;
}

export interface Metric {
  metric_id: number;
  name: string;
  business_meaning: string | null;
  calculation_formula: string | null;
  query_logic: string | null;
  unit: string | null;
  data_source: string | null;
  refresh_cycle: string | null;
  created_by: string | null;
  created_time: string | null;
  updated_by: string | null;
  updated_time: string | null;
}

export interface ObjectRelationship {
  relationship_id: number;
  object_id_1: number;
  object_id_2: number;
  relationship_type: string | null;
  join_logic: string | null;
  constraint_logic: string | null;
  join_direction: string | null;
  union_logic: string | null;
  created_by: string | null;
  created_time: string | null;
  updated_by: string | null;
  updated_time: string | null;
}

export interface DataAsset {
  id: number;
  datasource_name: string;
  table_name: string;
  table_comment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ActivityEntityRel {
  id: number;
  activity_id: number;
  entity_name: string;
  entity_type: string | null;
  order_index: number | null;
  created_time: string | null;
}

export type DatasourceSubTab = "connections" | "ontology" | "dataassets";

// ── User Datasources ────────────────────────────────────

export interface UserDatasource {
  id: number;
  tenant_id: number;
  name: string;
  dsn: string;
  db_type: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// ── Tenant ──────────────────────────────────────────────

export interface Tenant {
  id: number;
  name: string;
  description: string | null;
  created_by_user_id: number | null;
  created_at: string;
}

export interface TenantMember {
  id: number;
  tenant_id: number;
  user_id: number;
  username: string;
  user_role: string;
  role: string;
  joined_at: string;
}

// ── Debug ──────────────────────────────────────────────

export interface DebugEvent {
  event_id: number;
  conversation_id: number;
  message_id: number | null;
  step_id: number | null;
  seq: string;
  category: DebugCategory;
  data: Record<string, unknown>;
  timestamp: string;
}
