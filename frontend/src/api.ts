import i18n from "./i18n";
import type {
  LoginResponse,
  User,
  Conversation,
  ConversationDetail,
  StorageItem,
  TableInfo,
  ColumnInfo,
  DebugEvent,
  ChatRequest,
  SSEEvent,
  BusinessActivity,
  BusinessObject,
  BusinessRule,
  Metric,
  ObjectRelationship,
  DataAsset,
  ActivityEntityRel,
  UserDatasource,
  Tenant,
  TenantMember,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE || "/api";

// ── 401 handler ────────────────────────────────────────
// When a 401 is received, clear auth state so App.tsx shows LoginPage.
let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(fn: () => void) {
  onUnauthorized = fn;
}

function handleUnauthorized() {
  if (onUnauthorized) onUnauthorized();
}

export async function request<T>(
  path: string,
  token?: string,
  options?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error(i18n.t("api.loginExpired"));
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ───────────────────────────────────────────────

export async function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", undefined, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getMe(token: string): Promise<User> {
  return request<User>("/auth/me", token);
}

export async function resetPassword(
  token: string,
  target_username: string,
  new_password: string,
): Promise<{ message: string }> {
  return request<{ message: string }>("/auth/reset-password", token, {
    method: "POST",
    body: JSON.stringify({ target_username, new_password }),
  });
}

// ── Conversations ──────────────────────────────────────

export async function listConversations(
  token: string,
): Promise<Conversation[]> {
  return request<Conversation[]>("/conversations", token);
}

export async function createConversation(
  token: string,
  title?: string,
): Promise<Conversation> {
  return request<Conversation>("/conversations", token, {
    method: "POST",
    body: JSON.stringify({ title: title || null }),
  });
}

export async function getConversation(
  token: string,
  id: number,
): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`, token);
}

export async function deleteConversation(
  token: string,
  id: number,
): Promise<void> {
  await request(`/conversations/${id}`, token, { method: "DELETE" });
}

// ── Storage ────────────────────────────────────────────

export async function listStorage(
  token: string,
  prefix?: string,
): Promise<StorageItem[]> {
  const q = prefix ? `?prefix=${encodeURIComponent(prefix)}` : "";
  return request<StorageItem[]>(`/storage/list${q}`, token);
}

export async function readStorage(
  token: string,
  key: string,
): Promise<{ key: string; content: string }> {
  return request(`/storage/read?key=${encodeURIComponent(key)}`, token);
}

// ── Datasource ─────────────────────────────────────────

export async function listTables(token: string, datasourceId?: number): Promise<TableInfo[]> {
  const q = datasourceId !== undefined ? `?datasource_id=${datasourceId}` : "";
  return request<TableInfo[]>(`/datasource/tables${q}`, token);
}

export async function getColumns(
  token: string,
  datasourceId: number | null,
  table: string,
): Promise<ColumnInfo[]> {
  const q = datasourceId !== null && datasourceId !== undefined
    ? `?datasource_id=${datasourceId}`
    : "";
  return request<ColumnInfo[]>(
    `/datasource/table/${encodeURIComponent(table)}/columns${q}`,
    token,
  );
}

// ── Debug ──────────────────────────────────────────────

export async function getDebugEvents(
  token: string,
  conversationId: number,
): Promise<DebugEvent[]> {
  return request<DebugEvent[]>(`/debug/conversation/${conversationId}`, token);
}

// ── Chat (SSE streaming) ──────────────────────────────

export async function* streamChat(
  token: string,
  body: ChatRequest,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error(i18n.t("api.loginExpired"));
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith("data: ")) continue;
      const payload = trimmed.slice(6);
      if (!payload) continue;
      try {
        yield JSON.parse(payload) as SSEEvent;
      } catch {
        // skip malformed lines
      }
    }
  }

  // Process remaining buffer
  const remaining = buffer.trim();
  if (remaining && remaining.startsWith("data: ")) {
    const payload = remaining.slice(6);
    if (payload) {
      try {
        yield JSON.parse(payload) as SSEEvent;
      } catch {
        // skip
      }
    }
  }
}

// ── Ontology: Business Activities ─────────────────────

export async function listActivities(
  token: string,
): Promise<BusinessActivity[]> {
  return request<BusinessActivity[]>("/ontology/activities", token);
}

export async function createActivity(
  token: string,
  data: Omit<BusinessActivity, "activity_id" | "created_time" | "updated_time">,
): Promise<BusinessActivity> {
  return request<BusinessActivity>("/ontology/activities", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateActivity(
  token: string,
  activityId: number,
  data: Partial<BusinessActivity>,
): Promise<BusinessActivity> {
  return request<BusinessActivity>(`/ontology/activities/${activityId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteActivity(
  token: string,
  activityId: number,
): Promise<void> {
  await request(`/ontology/activities/${activityId}`, token, {
    method: "DELETE",
  });
}

// ── Ontology: Business Objects ────────────────────────

export async function listObjects(token: string): Promise<BusinessObject[]> {
  return request<BusinessObject[]>("/ontology/objects", token);
}

export async function createObject(
  token: string,
  data: Omit<BusinessObject, "object_id" | "created_time" | "updated_time">,
): Promise<BusinessObject> {
  return request<BusinessObject>("/ontology/objects", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateObject(
  token: string,
  objectId: number,
  data: Partial<BusinessObject>,
): Promise<BusinessObject> {
  return request<BusinessObject>(`/ontology/objects/${objectId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteObject(
  token: string,
  objectId: number,
): Promise<void> {
  await request(`/ontology/objects/${objectId}`, token, {
    method: "DELETE",
  });
}

// ── Ontology: Business Rules ──────────────────────────

export async function listRules(token: string): Promise<BusinessRule[]> {
  return request<BusinessRule[]>("/ontology/rules", token);
}

export async function createRule(
  token: string,
  data: Omit<BusinessRule, "rule_id" | "created_time" | "updated_time">,
): Promise<BusinessRule> {
  return request<BusinessRule>("/ontology/rules", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateRule(
  token: string,
  ruleId: number,
  data: Partial<BusinessRule>,
): Promise<BusinessRule> {
  return request<BusinessRule>(`/ontology/rules/${ruleId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteRule(
  token: string,
  ruleId: number,
): Promise<void> {
  await request(`/ontology/rules/${ruleId}`, token, {
    method: "DELETE",
  });
}

// ── Ontology: Metrics ─────────────────────────────────

export async function listMetrics(token: string): Promise<Metric[]> {
  return request<Metric[]>("/ontology/metrics", token);
}

export async function createMetric(
  token: string,
  data: Omit<Metric, "metric_id" | "created_time" | "updated_time">,
): Promise<Metric> {
  return request<Metric>("/ontology/metrics", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateMetric(
  token: string,
  metricId: number,
  data: Partial<Metric>,
): Promise<Metric> {
  return request<Metric>(`/ontology/metrics/${metricId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteMetric(
  token: string,
  metricId: number,
): Promise<void> {
  await request(`/ontology/metrics/${metricId}`, token, {
    method: "DELETE",
  });
}

// ── Ontology: Object Relationships ────────────────────

export async function listObjectRelationships(
  token: string,
): Promise<ObjectRelationship[]> {
  return request<ObjectRelationship[]>("/ontology/object-relationships", token);
}

export async function createObjectRelationship(
  token: string,
  data: Omit<ObjectRelationship, "relationship_id" | "created_time" | "updated_time">,
): Promise<ObjectRelationship> {
  return request<ObjectRelationship>("/ontology/object-relationships", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteObjectRelationship(
  token: string,
  relationshipId: number,
): Promise<void> {
  await request(`/ontology/object-relationships/${relationshipId}`, token, {
    method: "DELETE",
  });
}

// ── Ontology: Data Assets ─────────────────────────────

export async function listDataAssets(token: string, datasourceId?: number): Promise<DataAsset[]> {
  const q = datasourceId !== undefined ? `?datasource_id=${datasourceId}` : "";
  return request<DataAsset[]>(`/ontology/data-assets${q}`, token);
}

export async function createDataAsset(
  token: string,
  data: { datasource_name: string; table_name: string; table_comment?: string },
): Promise<DataAsset> {
  return request<DataAsset>("/ontology/data-assets", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteDataAsset(
  token: string,
  assetId: number,
): Promise<void> {
  await request(`/ontology/data-assets/${assetId}`, token, {
    method: "DELETE",
  });
}

// ── User Datasources ────────────────────────────────────

export async function listUserDatasources(
  token: string,
): Promise<UserDatasource[]> {
  return request<UserDatasource[]>("/user/datasources", token);
}

export async function createUserDatasource(
  token: string,
  data: { name: string; dsn: string; db_type?: string },
): Promise<UserDatasource> {
  return request<UserDatasource>("/user/datasources", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateUserDatasource(
  token: string,
  id: number,
  data: { name?: string; dsn?: string; db_type?: string },
): Promise<UserDatasource> {
  return request<UserDatasource>(`/user/datasources/${id}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function activateDatasource(
  token: string,
  id: number,
): Promise<{ status: string; active_datasource_id: number }> {
  return request<{ status: string; active_datasource_id: number }>(
    `/user/datasources/${id}/activate`,
    token,
    { method: "PUT" },
  );
}

export async function deleteUserDatasource(
  token: string,
  id: number,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/user/datasources/${id}`, token, {
    method: "DELETE",
  });
}

export async function testDatasourceConnection(
  token: string,
  dsn: string,
  db_type: string,
): Promise<{ status: string; detail?: string }> {
  return request<{ status: string; detail?: string }>(
    "/user/datasources/test",
    token,
    {
      method: "POST",
      body: JSON.stringify({ dsn, db_type }),
    },
  );
}

// ── Tenants ─────────────────────────────────────────────

export async function listTenants(token: string): Promise<Tenant[]> {
  return request<Tenant[]>("/tenants", token);
}

export async function createTenant(
  token: string,
  data: { name: string; description?: string },
): Promise<Tenant> {
  return request<Tenant>("/tenants", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTenant(
  token: string,
  id: number,
  data: { name?: string; description?: string },
): Promise<Tenant> {
  return request<Tenant>(`/tenants/${id}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteTenant(
  token: string,
  id: number,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/tenants/${id}`, token, {
    method: "DELETE",
  });
}

export async function listTenantMembers(
  token: string,
  tenantId: number,
): Promise<TenantMember[]> {
  return request<TenantMember[]>(`/tenants/${tenantId}/members`, token);
}

export async function addTenantMember(
  token: string,
  tenantId: number,
  data: { user_id: number; role: string },
): Promise<TenantMember> {
  return request<TenantMember>(`/tenants/${tenantId}/members`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function removeTenantMember(
  token: string,
  tenantId: number,
  userId: number,
): Promise<{ status: string }> {
  return request<{ status: string }>(
    `/tenants/${tenantId}/members/${userId}`,
    token,
    { method: "DELETE" },
  );
}

// ── Ontology: Activity Entity Relations ───────────────

export async function listActivityEntityRels(
  token: string,
  activityId?: number,
): Promise<ActivityEntityRel[]> {
  const q = activityId !== undefined ? `?activity_id=${activityId}` : "";
  return request<ActivityEntityRel[]>(`/ontology/activity-entity-rels${q}`, token);
}
