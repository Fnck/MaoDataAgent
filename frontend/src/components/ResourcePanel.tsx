import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { UserDatasource, DatasourceSubTab } from "../types";
import OntologyManagement from "./OntologyManagement";
import DataAssetsManagement from "./DataAssetsManagement";
import DatasourceForm from "./DatasourceForm";

export default function ResourcePanel() {
  const { t } = useTranslation();
  const datasourceSubTab = useStore((s) => s.datasourceSubTab);
  const setDatasourceSubTab = useStore((s) => s.setDatasourceSubTab);
  const userDatasources = useStore((s) => s.userDatasources);
  const activeDatasourceId = useStore((s) => s.activeDatasourceId);
  const fetchActivities = useStore((s) => s.fetchActivities);
  const fetchObjects = useStore((s) => s.fetchObjects);
  const fetchRules = useStore((s) => s.fetchRules);
  const fetchMetrics = useStore((s) => s.fetchMetrics);
  const fetchDataAssets = useStore((s) => s.fetchDataAssets);
  const fetchObjectRelationships = useStore((s) => s.fetchObjectRelationships);
  const [fetched, setFetched] = useState(false);

  const activeDs = userDatasources.find((d) => d.id === activeDatasourceId);
  const activeDsName = activeDs?.name || "";

  const SUB_TABS: { key: DatasourceSubTab; label: string }[] = [
    { key: "connections", label: t("datasources.tabConnections") },
    { key: "ontology", label: t("resourcePanel.ontology") },
    { key: "dataassets", label: t("resourcePanel.assets") },
  ];

  // Fetch ontology data once when the component mounts
  useEffect(() => {
    if (!fetched) {
      setFetched(true);
      fetchActivities();
      fetchObjects();
      fetchRules();
      fetchMetrics();
      fetchDataAssets();
      fetchObjectRelationships();
    }
  }, [fetched, fetchActivities, fetchObjects, fetchRules, fetchMetrics, fetchDataAssets, fetchObjectRelationships]);

  return (
    <div className="flex flex-col h-full">
      {/* Active Datasource Indicator */}
      {activeDs ? (
        <div className="px-3 py-2.5 bg-gradient-to-r from-emerald-50 to-brand-50 border-b border-emerald-200/60 shrink-0">
          <div className="flex items-center gap-2.5">
            {/* Status dot */}
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-surface-800 truncate">{activeDs.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold leading-none">
                  {t("datasources.connected")}
                </span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <svg className="w-3 h-3 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
                </svg>
                <span className="text-xs text-surface-500">{dbTypeLabel(activeDs.db_type)}</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="px-3 py-3 bg-surface-100 border-b border-surface-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-surface-300"></span>
            <div>
              <span className="text-sm font-semibold text-surface-500">{t("datasources.noActive")}</span>
              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-surface-200 text-surface-500 font-semibold">
                {t("datasources.notConnected")}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Sub-tabs - pill style */}
      <div className="flex gap-1 p-2 shrink-0">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setDatasourceSubTab(tab.key)}
            className={datasourceSubTab === tab.key ? "tab-active flex-1" : "tab-inactive flex-1"}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {datasourceSubTab === "connections" && <ConnectionsPanel />}
        {datasourceSubTab === "ontology" && (
          <div className="h-full">
            <OntologyManagement compact datasourceName={activeDsName} />
          </div>
        )}
        {datasourceSubTab === "dataassets" && (
          <div className="h-full">
            <DataAssetsManagement compact datasourceName={activeDsName} datasourceId={activeDatasourceId ?? undefined} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────

function dbTypeLabel(type: string) {
  switch (type) {
    case "postgres": return "PostgreSQL";
    case "sqlite": return "SQLite";
    case "mysql": return "MySQL";
    default: return type;
  }
}

// ── Connections Sub-tab ────────────────────────────────

function ConnectionsPanel() {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const userDatasources = useStore((s) => s.userDatasources);
  const activeDatasourceId = useStore((s) => s.activeDatasourceId);
  const fetchUserDatasources = useStore((s) => s.fetchUserDatasources);
  const activateDatasource = useStore((s) => s.activateDatasource);
  const removeDatasource = useStore((s) => s.removeDatasource);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<UserDatasource | null>(null);
  const [testResults, setTestResults] = useState<Record<number, string | null>>({});
  const [testing, setTesting] = useState<number | null>(null);

  useEffect(() => {
    fetchUserDatasources();
  }, [fetchUserDatasources]);

  const handleSwitch = async (id: number) => {
    if (id === activeDatasourceId) return;
    await activateDatasource(id);
  };

  const handleDelete = async (ds: UserDatasource) => {
    if (ds.is_active) {
      alert(t("datasources.deleteActive"));
      return;
    }
    if (ds.is_default) {
      alert(t("datasources.deleteDefault"));
      return;
    }
    if (!confirm(t("datasources.confirmDelete"))) return;
    await removeDatasource(ds.id);
  };

  const handleTest = async (ds: UserDatasource) => {
    setTesting(ds.id);
    setTestResults((prev) => ({ ...prev, [ds.id]: null }));
    try {
      const result = await api.testDatasourceConnection(
        token,
        ds.dsn,
        ds.db_type,
      );
      setTestResults((prev) => ({
        ...prev,
        [ds.id]:
          result.status === "ok"
            ? t("datasources.testOk")
            : result.detail || t("datasources.testFailed"),
      }));
    } catch (e: unknown) {
      setTestResults((prev) => ({
        ...prev,
        [ds.id]: e instanceof Error ? e.message : t("datasources.connectionFailed"),
      }));
    } finally {
      setTesting(null);
    }
  };

  const handleEdit = (ds: UserDatasource) => {
    setEditing(ds);
    setShowForm(true);
  };

  const handleAdd = () => {
    setEditing(null);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditing(null);
  };

  const handleFormSaved = () => {
    setShowForm(false);
    setEditing(null);
    fetchUserDatasources();
  };

  return (
    <div className="p-3">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-surface-700">
          {t("datasources.tabConnections")}
        </span>
        <button
          onClick={handleAdd}
          className="text-xs px-2.5 py-1 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors"
        >
          {t("datasources.add")}
        </button>
      </div>

      {userDatasources.length === 0 ? (
        <div className="text-center text-surface-400 text-sm py-6">
          {t("datasources.noDatasources")}
        </div>
      ) : (
        userDatasources.map((ds) => (
          <div
            key={ds.id}
            className={`mb-2 p-3 rounded-xl border transition-all duration-200 ${
              ds.is_active
                ? "border-brand-300 bg-brand-50"
                : "border-surface-200 bg-white hover:border-surface-300"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-surface-800 truncate">{ds.name}</span>
              {ds.is_active && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                  {t("datasources.active")}
                </span>
              )}
              {ds.is_default && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-200 text-surface-600 font-medium">
                  {t("datasources.default")}
                </span>
              )}
            </div>
            <div className="text-xs text-surface-400 mb-2">{dbTypeLabel(ds.db_type)}</div>
            <div className="flex items-center gap-1.5">
              {!ds.is_active && (
                <button
                  onClick={() => handleSwitch(ds.id)}
                  className="text-xs px-2 py-1 rounded-lg bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
                >
                  {t("datasources.switch")}
                </button>
              )}
              {!ds.is_default && (
                <>
                  <button
                    onClick={() => handleEdit(ds)}
                    className="text-xs px-2 py-1 rounded-lg bg-surface-100 text-surface-600 hover:bg-surface-200 transition-colors"
                  >
                    {t("datasources.edit")}
                  </button>
                  <button
                    onClick={() => handleDelete(ds)}
                    className="text-xs px-2 py-1 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                  >
                    {t("datasources.delete")}
                  </button>
                </>
              )}
              <button
                onClick={() => handleTest(ds)}
                disabled={testing === ds.id}
                className="text-xs px-2 py-1 rounded-lg bg-surface-100 text-surface-600 hover:bg-surface-200 transition-colors disabled:opacity-50"
              >
                {testing === ds.id ? t("datasources.testing") : t("datasources.test")}
              </button>
            </div>
            {testResults[ds.id] && (
              <div
                className={`mt-2 text-xs px-2 py-1 rounded ${
                  testResults[ds.id] === t("datasources.testOk")
                    ? "bg-green-50 text-green-700"
                    : "bg-red-50 text-red-700"
                }`}
              >
                {testResults[ds.id]}
              </div>
            )}
          </div>
        ))
      )}

      {showForm && (
        <DatasourceForm
          editing={editing}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}
    </div>
  );
}
