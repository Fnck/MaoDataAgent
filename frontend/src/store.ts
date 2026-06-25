import { create } from "zustand";
import type {
  User,
  Conversation,
  Message,
  WorkflowStep,
  DebugEvent,
  BusinessActivity,
  BusinessObject,
  BusinessRule,
  Metric,
  DataAsset,
  ObjectRelationship,
  DatasourceSubTab,
  UserDatasource,
  Tenant,
} from "./types";
import * as api from "./api";

// ── Persist token to localStorage ─────────────────────

function loadToken(): string | null {
  return localStorage.getItem("dataagent_token");
}
function saveToken(token: string | null) {
  if (token) localStorage.setItem("dataagent_token", token);
  else localStorage.removeItem("dataagent_token");
}
function loadUser(): User | null {
  const raw = localStorage.getItem("dataagent_user");
  return raw ? JSON.parse(raw) : null;
}
function saveUser(user: User | null) {
  if (user) localStorage.setItem("dataagent_user", JSON.stringify(user));
  else localStorage.removeItem("dataagent_user");
}

// ── Store ──────────────────────────────────────────────

interface AppStore {
  // Auth
  token: string | null;
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;

  // Conversations
  conversations: Conversation[];
  currentConversationId: number | null;
  messages: Message[];
  fetchingConversation: boolean;
  fetchConversations: () => Promise<void>;
  createConversation: (title?: string) => Promise<number>;
  selectConversation: (id: number) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;

  // Messages (mutated during streaming)
  addMessage: (msg: Message) => void;
  appendToLastAssistant: (content: string) => void;
  setLastAssistantMessageId: (id: number) => void;

  // Context
  selectedFiles: string[];
  selectedTables: string[];
  toggleFile: (file: string) => void;
  toggleTable: (table: string) => void;
  clearContext: () => void;

  // UI
  leftSidebarOpen: boolean;
  resourcePanelOpen: boolean;
  toggleLeftSidebar: () => void;
  toggleResourcePanel: () => void;

  // Debug
  debugEvents: DebugEvent[];
  debugDrawerOpen: boolean;
  addDebugEvent: (event: DebugEvent) => void;
  clearDebugEvents: () => void;
  assignDebugEventMessageId: (messageId: number) => void;
  openDebugDrawer: () => void;
  closeDebugDrawer: () => void;

  // Workflow
  workflowSteps: WorkflowStep[];
  setWorkflowStep: (step: WorkflowStep) => void;
  updateWorkflowStep: (stepId: number, updates: Partial<WorkflowStep>) => void;
  clearWorkflowSteps: () => void;

  // Streaming
  isStreaming: boolean;
  setStreaming: (v: boolean) => void;

  // Ontology Navigation (via right panel tab)
  datasourceSubTab: DatasourceSubTab;
  setDatasourceSubTab: (tab: DatasourceSubTab) => void;
  openOntologyPanel: () => void;
  openDataAssetsPanel: () => void;

  // Ontology Data
  activities: BusinessActivity[];
  objects: BusinessObject[];
  rules: BusinessRule[];
  metrics: Metric[];
  dataAssets: DataAsset[];
  objectRelationships: ObjectRelationship[];
  fetchActivities: () => Promise<void>;
  fetchObjects: () => Promise<void>;
  fetchRules: () => Promise<void>;
  fetchMetrics: () => Promise<void>;
  fetchDataAssets: () => Promise<void>;
  fetchObjectRelationships: () => Promise<void>;

  // User Datasources
  userDatasources: UserDatasource[];
  activeDatasourceId: number | null;
  fetchUserDatasources: () => Promise<void>;
  activateDatasource: (id: number) => Promise<void>;
  removeDatasource: (id: number) => Promise<void>;

  // Tenant
  currentTenantId: number | null;
  tenants: Tenant[];
  fetchTenants: () => Promise<void>;
  switchTenant: (tenantId: number) => Promise<void>;
}

export const useStore = create<AppStore>((set, get) => ({
  // ── Auth ───────────────────────────────────────────
  token: loadToken(),
  user: loadUser(),

  login: async (username, password) => {
    const res = await api.login(username, password);
    saveToken(res.token);
    saveUser(res.user);
    set({ token: res.token, user: res.user });
  },

  logout: () => {
    saveToken(null);
    saveUser(null);
    set({
      token: null,
      user: null,
      conversations: [],
      currentConversationId: null,
      messages: [],
    });
  },

  // ── Conversations ──────────────────────────────────
  conversations: [],
  currentConversationId: null,
  messages: [],
  fetchingConversation: false,

  fetchConversations: async () => {
    const token = get().token;
    if (!token) return;
    const convs = await api.listConversations(token);
    set({ conversations: convs });
  },

  createConversation: async (title) => {
    const token = get().token;
    if (!token) return -1;
    const conv = await api.createConversation(token, title);
    set((s) => ({ conversations: [conv, ...s.conversations] }));
    return conv.id;
  },

  selectConversation: async (id) => {
    const token = get().token;
    if (!token) return;
    const switching = get().currentConversationId !== id;
    const prevDebugs = switching ? [] : get().debugEvents;
    set({
      currentConversationId: id,
      fetchingConversation: true,
      messages: [],
      debugEvents: prevDebugs,
    });
    try {
      const detail = await api.getConversation(token, id);
      const apiDebugs = await api.getDebugEvents(token, id);

      // Merge API events with in-memory events, dedup by event_id
      // When switching conversations, prevDebugs is [] so only API events are used
      const apiEventIds = new Set(apiDebugs.map((e) => e.event_id));
      let merged = [
        ...prevDebugs.filter((e) => !apiEventIds.has(e.event_id)),
        ...apiDebugs,
      ];

      set({ messages: detail.messages, debugEvents: merged });
    } finally {
      set({ fetchingConversation: false });
    }
  },

  deleteConversation: async (id) => {
    const token = get().token;
    if (!token) return;
    await api.deleteConversation(token, id);
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      currentConversationId: s.currentConversationId === id ? null : s.currentConversationId,
      messages: s.currentConversationId === id ? [] : s.messages,
    }));
  },

  // ── Messages ───────────────────────────────────────
  addMessage: (msg) => {
    set((s) => ({ messages: [...s.messages, msg] }));
  },

  appendToLastAssistant: (content) => {
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content: msgs[i].content + content };
          break;
        }
      }
      return { messages: msgs };
    });
  },

  setLastAssistantMessageId: (id) => {
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], id };
          break;
        }
      }
      return { messages: msgs };
    });
  },

  // ── Context ────────────────────────────────────────
  selectedFiles: [],
  selectedTables: [],

  toggleFile: (file) => {
    set((s) => ({
      selectedFiles: s.selectedFiles.includes(file)
        ? s.selectedFiles.filter((f) => f !== file)
        : [...s.selectedFiles, file],
    }));
  },

  toggleTable: (table) => {
    set((s) => ({
      selectedTables: s.selectedTables.includes(table)
        ? s.selectedTables.filter((t) => t !== table)
        : [...s.selectedTables, table],
    }));
  },

  clearContext: () => set({ selectedFiles: [], selectedTables: [] }),

  // ── UI ─────────────────────────────────────────────
  leftSidebarOpen: true,
  resourcePanelOpen: true,

  toggleLeftSidebar: () => set((s) => ({ leftSidebarOpen: !s.leftSidebarOpen })),
  toggleResourcePanel: () => set((s) => ({ resourcePanelOpen: !s.resourcePanelOpen })),

  // ── Debug ──────────────────────────────────────────
  debugEvents: [],
  debugDrawerOpen: false,

  addDebugEvent: (event) => set((s) => ({ debugEvents: [...s.debugEvents, event] })),

  clearDebugEvents: () => set({ debugEvents: [] }),

  assignDebugEventMessageId: (messageId) => set((s) => ({
    debugEvents: s.debugEvents.map((e) =>
      e.message_id === null ? { ...e, message_id: messageId } : e
    ),
  })),

  openDebugDrawer: () => set({ debugDrawerOpen: true }),
  closeDebugDrawer: () => set({ debugDrawerOpen: false }),

  // ── Workflow ──────────────────────────────────────
  workflowSteps: [],

  setWorkflowStep: (step) => {
    set((s) => {
      const existing = s.workflowSteps.findIndex((w) => w.step_id === step.step_id);
      if (existing >= 0) {
        const steps = [...s.workflowSteps];
        steps[existing] = step;
        return { workflowSteps: steps };
      }
      return { workflowSteps: [...s.workflowSteps, step] };
    });
  },

  updateWorkflowStep: (stepId, updates) => {
    set((s) => {
      const idx = s.workflowSteps.findIndex((w) => w.step_id === stepId);
      if (idx < 0) return s;
      const steps = [...s.workflowSteps];
      steps[idx] = { ...steps[idx], ...updates };
      return { workflowSteps: steps };
    });
  },

  clearWorkflowSteps: () => set({ workflowSteps: [] }),

  // ── Streaming ──────────────────────────────────────
  isStreaming: false,
  setStreaming: (v) => set({ isStreaming: v }),

  // ── Resource Panel Tab Control ───────────────────
  datasourceSubTab: "connections",
  setDatasourceSubTab: (tab) => set({ datasourceSubTab: tab, resourcePanelOpen: true }),
  openOntologyPanel: () => set({ resourcePanelOpen: true, datasourceSubTab: "ontology" }),
  openDataAssetsPanel: () => set({ resourcePanelOpen: true, datasourceSubTab: "dataassets" }),

  // ── Ontology Data ──────────────────────────────────
  activities: [],
  objects: [],
  rules: [],
  metrics: [],
  dataAssets: [],
  objectRelationships: [],

  fetchActivities: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listActivities(token);
    set({ activities: data });
  },

  fetchObjects: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listObjects(token);
    set({ objects: data });
  },

  fetchRules: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listRules(token);
    set({ rules: data });
  },

  fetchMetrics: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listMetrics(token);
    set({ metrics: data });
  },

  fetchDataAssets: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listDataAssets(token, get().activeDatasourceId ?? undefined);
    set({ dataAssets: data });
  },

  fetchObjectRelationships: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listObjectRelationships(token);
    set({ objectRelationships: data });
  },

  // ── User Datasources ───────────────────────────────
  userDatasources: [],
  activeDatasourceId: null,

  fetchUserDatasources: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listUserDatasources(token);
    const active = data.find((d) => d.is_active);
    set({ userDatasources: data, activeDatasourceId: active?.id ?? null });
  },

  activateDatasource: async (id) => {
    const token = get().token;
    if (!token) return;
    await api.activateDatasource(token, id);
    // Refresh list and clear context since tables are from different DB
    const data = await api.listUserDatasources(token);
    const active = data.find((d) => d.is_active);
    set({
      userDatasources: data,
      activeDatasourceId: active?.id ?? null,
      selectedTables: [],
    });
  },

  removeDatasource: async (id) => {
    const token = get().token;
    if (!token) return;
    await api.deleteUserDatasource(token, id);
    const data = await api.listUserDatasources(token);
    const active = data.find((d) => d.is_active);
    set({ userDatasources: data, activeDatasourceId: active?.id ?? null });
  },

  // ── Tenant ──────────────────────────────────────────
  currentTenantId: null,
  tenants: [],

  fetchTenants: async () => {
    const token = get().token;
    if (!token) return;
    const data = await api.listTenants(token);
    // Default to first tenant
    const currentId = get().currentTenantId || data[0]?.id || null;
    set({ tenants: data, currentTenantId: currentId });
    // Also fetch datasources for the current tenant
    if (currentId) {
      get().fetchUserDatasources();
    }
  },

  switchTenant: async (tenantId) => {
    set({
      currentTenantId: tenantId,
      userDatasources: [],
      activeDatasourceId: null,
      selectedTables: [],
    });
    // Refresh tenant-scoped data
    const { fetchUserDatasources, fetchActivities, fetchObjects, fetchRules, fetchMetrics, fetchDataAssets } = get();
    await fetchUserDatasources();
    fetchActivities();
    fetchObjects();
    fetchRules();
    fetchMetrics();
    fetchDataAssets();
  },
}));
