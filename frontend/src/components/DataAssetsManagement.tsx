import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { TableInfo } from "../types";

export default function DataAssetsManagement({ compact = false, datasourceName = "", datasourceId }: { compact?: boolean; datasourceName?: string; datasourceId?: number }) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const dataAssets = useStore((s) => s.dataAssets);
  const activities = useStore((s) => s.activities);
  const objects = useStore((s) => s.objects);
  const fetchDataAssets = useStore((s) => s.fetchDataAssets);
  const fetchActivities = useStore((s) => s.fetchActivities);
  const fetchObjects = useStore((s) => s.fetchObjects);

  const [availableTables, setAvailableTables] = useState<TableInfo[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [bindModal, setBindModal] = useState<{
    assetId: number;
    tableName: string;
  } | null>(null);
  const [bindType, setBindType] = useState<"activity" | "object">("object");
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [entityType, setEntityType] = useState<"INPUT" | "OUTPUT">("INPUT");

  useEffect(() => {
    fetchDataAssets();
    fetchActivities();
    fetchObjects();
  }, [fetchDataAssets, fetchActivities, fetchObjects]);

  // Re-fetch when datasource changes
  useEffect(() => {
    if (datasourceName) {
      fetchDataAssets();
    }
  }, [datasourceName, fetchDataAssets]);

  // Filter managed data assets by active datasource
  const filteredDataAssets = datasourceName
    ? dataAssets.filter((a) => a.datasource_name === datasourceName)
    : dataAssets;

  const loadAvailableTables = async () => {
    setLoadingTables(true);
    try {
      const tables = await api.listTables(token, datasourceId);
      // Filter tables by active datasource if specified
      const filteredTables = datasourceName
        ? tables.filter((t) => t.datasource_name === datasourceName)
        : tables;
      const managedNames = new Set(
        filteredDataAssets.map((a) => `${a.datasource_name}:${a.table_name}`)
      );
      const available = filteredTables.filter(
        (t) => !managedNames.has(`${t.datasource_name}:${t.table_name}`)
      );
      setAvailableTables(available);
    } finally {
      setLoadingTables(false);
    }
  };

  const handleAddToManaged = async (table: TableInfo) => {
    try {
      await api.createDataAsset(token, {
        datasource_name: table.datasource_name,
        table_name: table.table_name,
      });
      fetchDataAssets();
      setAvailableTables((prev) =>
        prev.filter(
          (t) =>
            !(
              t.datasource_name === table.datasource_name &&
              t.table_name === table.table_name
            )
        )
      );
    } catch (err) {
      // Duplicate or other error
    }
  };

  const handleRemoveFromManaged = async (assetId: number) => {
    await api.deleteDataAsset(token, assetId);
    fetchDataAssets();
  };

  const handleOpenBind = (assetId: number, tableName: string) => {
    setBindModal({ assetId, tableName });
    setSelectedTargetId(null);
    setBindType("object");
    setEntityType("INPUT");
  };

  const handleBind = async () => {
    if (!bindModal || !selectedTargetId) return;

    if (bindType === "object") {
      const obj = objects.find((o) => o.object_id === selectedTargetId);
      if (!obj) return;
      const currentEntities = obj.related_entities
        ? obj.related_entities.split(",").map((s) => s.trim())
        : [];
      if (!currentEntities.includes(bindModal.tableName)) {
        currentEntities.push(bindModal.tableName);
      }
      await api.updateObject(token, selectedTargetId, {
        related_entities: currentEntities.join(", "),
      });
      fetchObjects();
    } else {
      const existingRels = await api.listActivityEntityRels(token, selectedTargetId);
      const exists = existingRels.some(
        (r) =>
          r.entity_name === bindModal.tableName && r.entity_type === entityType
      );
      if (!exists) {
        await api.listActivityEntityRels(token, undefined);
        await fetch(
          `${window.location.origin}/api/ontology/activity-entity-rels`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              activity_id: selectedTargetId,
              entity_name: bindModal.tableName,
              entity_type: entityType,
            }),
          }
        );
        fetchActivities();
      }
    }

    setBindModal(null);
  };

  return (
    <div className={`h-full overflow-y-auto ${compact ? "p-3" : "p-5"}`}>
      {/* Datasource context banner */}
      {datasourceName ? (
        <div className="mb-3 px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-50 to-brand-50 border border-emerald-200/60">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            <span className="text-xs text-surface-500">{t("datasources.active")}:</span>
            <span className="text-sm font-semibold text-surface-800">{datasourceName}</span>
          </div>
        </div>
      ) : (
        <div className="mb-3 px-3 py-2 rounded-xl bg-surface-100 border border-surface-200">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-surface-300"></span>
            <span className="text-xs text-surface-400">{t("datasources.noActive")}</span>
          </div>
        </div>
      )}
      <div className={compact ? "" : "max-w-6xl mx-auto"}>
        {!compact && (
          <h2 className="text-xl font-semibold text-surface-800 mb-5">
            {t("dataAssets.title")}
          </h2>
        )}

        <div className={compact ? "space-y-5" : "grid grid-cols-2 gap-6"}>
          {/* Left: Available Tables */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-surface-700">
                {t("dataAssets.availableTables")}
              </h3>
              <button
                onClick={loadAvailableTables}
                disabled={loadingTables}
                className="btn-secondary text-sm"
              >
                {loadingTables ? t("dataAssets.loading") : t("dataAssets.refresh")}
              </button>
            </div>
            {availableTables.length === 0 ? (
              <div className="p-10 text-center text-surface-400 text-sm border-2 border-dashed border-surface-300 rounded-2xl">
                {loadingTables
                  ? t("dataAssets.loadingTables")
                  : t("dataAssets.clickRefresh")}
              </div>
            ) : (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {availableTables.map((tbl, i) => (
                  <div
                    key={`${tbl.datasource_name}:${tbl.table_name}-${i}`}
                    className="p-3 bg-white border border-surface-200/60 rounded-xl shadow-xs hover:shadow-sm transition-all duration-200 ease-out flex justify-between items-center"
                  >
                    <div>
                      <p className="text-sm font-mono text-surface-800">{tbl.table_name}</p>
                      <p className="text-xs text-surface-400">{tbl.datasource_name}</p>
                    </div>
                    <button
                      onClick={() => handleAddToManaged(tbl)}
                      className="text-sm text-brand-500 font-medium hover:text-brand-700 rounded-lg px-2 py-1 hover:bg-brand-50 transition-colors"
                    >
                      {t("dataAssets.add")}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Managed Data Assets */}
          <div>
            <h3 className="text-sm font-semibold text-surface-700 mb-4">
              {t("dataAssets.managedAssets")} ({filteredDataAssets.length})
            </h3>
            {filteredDataAssets.length === 0 ? (
              <div className="p-10 text-center text-surface-400 text-sm border-2 border-dashed border-surface-300 rounded-2xl">
                {t("dataAssets.noAssets")}
                <br />
                {t("dataAssets.browseHint")}
              </div>
            ) : (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {filteredDataAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="p-3 bg-white border border-surface-200/60 rounded-xl shadow-xs hover:shadow-sm transition-all duration-200 ease-out"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-mono text-surface-800">{asset.table_name}</p>
                        <p className="text-xs text-surface-400">
                          {asset.datasource_name}
                        </p>
                        {asset.table_comment && (
                          <p className="text-xs text-surface-500 mt-0.5">
                            {asset.table_comment}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1.5 shrink-0">
                        <button
                          onClick={() =>
                            handleOpenBind(asset.id, asset.table_name)
                          }
                          className="text-sm text-brand-500 font-medium hover:text-brand-700 rounded-lg px-2 py-1 hover:bg-brand-50 transition-colors"
                          title={t("dataAssets.bind")}
                        >
                          {t("dataAssets.bind")}
                        </button>
                        <button
                          onClick={() => handleRemoveFromManaged(asset.id)}
                          className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 rounded-lg px-2 py-1 hover:bg-semantic-danger-50 transition-colors"
                        >
                          {t("dataAssets.remove")}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bind modal */}
        {bindModal && (
          <div className="fixed inset-0 bg-surface-900/30 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in">
            <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-glass animate-scale-in">
              <h2 className="text-xl font-semibold mb-5 text-surface-800">
                {t("dataAssets.bindTitle", { tableName: bindModal.tableName })}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1.5">
                    {t("dataAssets.bindTo")}
                  </label>
                  <select
                    value={bindType}
                    onChange={(e) => {
                      setBindType(e.target.value as "activity" | "object");
                      setSelectedTargetId(null);
                    }}
                    className="input"
                  >
                    <option value="object">{t("dataAssets.businessObject")}</option>
                    <option value="activity">{t("dataAssets.businessActivity")}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1.5">
                    {bindType === "object" ? t("dataAssets.object") : t("dataAssets.activity")}
                  </label>
                  <select
                    value={selectedTargetId || ""}
                    onChange={(e) =>
                      setSelectedTargetId(e.target.value ? parseInt(e.target.value) : null)
                    }
                    className="input"
                  >
                    <option value="">{t("dataAssets.selectPlaceholder")}</option>
                    {bindType === "object"
                      ? objects.map((o) => (
                          <option key={o.object_id} value={o.object_id}>
                            {o.name}
                          </option>
                        ))
                      : activities.map((a) => (
                          <option key={a.activity_id} value={a.activity_id}>
                            {a.name}
                          </option>
                        ))}
                  </select>
                </div>

                {bindType === "activity" && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1.5">
                      {t("dataAssets.entityType")}
                    </label>
                    <select
                      value={entityType}
                      onChange={(e) =>
                        setEntityType(e.target.value as "INPUT" | "OUTPUT")
                      }
                      className="input"
                    >
                      <option value="INPUT">INPUT</option>
                      <option value="OUTPUT">OUTPUT</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setBindModal(null)}
                  className="btn-secondary"
                >
                  {t("dataAssets.cancel")}
                </button>
                <button
                  onClick={handleBind}
                  disabled={!selectedTargetId}
                  className="btn-primary"
                >
                  {t("dataAssets.bind")}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
