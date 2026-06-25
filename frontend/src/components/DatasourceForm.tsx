import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { UserDatasource } from "../types";

interface Props {
  editing: UserDatasource | null;
  onClose: () => void;
  onSaved: () => void;
}

const DB_TYPES = [
  { value: "postgres", labelKey: "postgres" },
  { value: "sqlite", labelKey: "sqlite" },
  { value: "mysql", labelKey: "mysql" },
];

export default function DatasourceForm({ editing, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;

  const [name, setName] = useState(editing?.name || "");
  const [dsn, setDsn] = useState(editing?.dsn || "");
  const [dbType, setDbType] = useState(editing?.db_type || "postgres");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testOk, setTestOk] = useState(false);

  const isEditing = editing !== null;

  const handleTest = async () => {
    if (!dsn.trim()) return;
    setTesting(true);
    setTestResult(null);
    setTestOk(false);
    try {
      const result = await api.testDatasourceConnection(
        token,
        dsn.trim(),
        dbType,
      );
      if (result.status === "ok") {
        setTestResult(t("datasources.testOk"));
        setTestOk(true);
      } else {
        setTestResult(result.detail || t("datasources.testFailed"));
        setTestOk(false);
      }
    } catch (e: unknown) {
      setTestResult(
        e instanceof Error ? e.message : t("datasources.connectionFailed"),
      );
      setTestOk(false);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim() || !dsn.trim()) return;
    setSaving(true);
    try {
      if (isEditing) {
        await api.updateUserDatasource(token, editing.id, {
          name: name.trim(),
          dsn: dsn.trim(),
          db_type: dbType,
        });
      } else {
        await api.createUserDatasource(token, {
          name: name.trim(),
          dsn: dsn.trim(),
          db_type: dbType,
        });
      }
      onSaved();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : t("datasources.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const dsnPlaceholder =
    dbType === "sqlite"
      ? t("datasources.dsnSqlitePlaceholder")
      : t("datasources.dsnPlaceholder");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-2xl shadow-xl w-[420px] max-h-[90vh] overflow-y-auto p-6">
        <h3 className="text-lg font-semibold text-surface-800 mb-4">
          {isEditing ? t("datasources.editTitle") : t("datasources.createTitle")}
        </h3>

        {/* Name */}
        <div className="mb-3">
          <label className="block text-sm font-medium text-surface-600 mb-1">
            {t("datasources.name")}
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("datasources.namePlaceholder")}
            className="w-full px-3 py-2 rounded-xl border border-surface-200 text-sm focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400"
          />
        </div>

        {/* DB Type */}
        <div className="mb-3">
          <label className="block text-sm font-medium text-surface-600 mb-1">
            {t("datasources.dbType")}
          </label>
          <select
            value={dbType}
            onChange={(e) => {
              setDbType(e.target.value);
              setTestResult(null);
              setTestOk(false);
            }}
            className="w-full px-3 py-2 rounded-xl border border-surface-200 text-sm focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400 bg-white"
          >
            {DB_TYPES.map((dt) => (
              <option key={dt.value} value={dt.value}>
                {t(`datasources.${dt.labelKey}`)}
              </option>
            ))}
          </select>
        </div>

        {/* DSN */}
        <div className="mb-3">
          <label className="block text-sm font-medium text-surface-600 mb-1">
            {t("datasources.dsn")}
          </label>
          <input
            type="text"
            value={dsn}
            onChange={(e) => {
              setDsn(e.target.value);
              setTestResult(null);
              setTestOk(false);
            }}
            placeholder={dsnPlaceholder}
            className="w-full px-3 py-2 rounded-xl border border-surface-200 text-sm font-mono focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400"
          />
          <p className="text-xs text-surface-400 mt-1">{dsnPlaceholder}</p>
        </div>

        {/* Test Connection */}
        <div className="mb-4">
          <button
            onClick={handleTest}
            disabled={testing || !dsn.trim()}
            className="text-sm px-3 py-1.5 rounded-lg border border-surface-200 text-surface-600 hover:bg-surface-50 transition-colors disabled:opacity-50"
          >
            {testing ? t("datasources.testing") : t("datasources.test")}
          </button>

          {testResult && (
            <div
              className={`mt-2 text-sm px-3 py-2 rounded-xl ${
                testOk
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {testResult}
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm text-surface-600 hover:bg-surface-100 transition-colors"
          >
            {t("datasources.cancel")}
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || !dsn.trim()}
            className="px-4 py-2 rounded-xl text-sm bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50"
          >
            {saving ? t("datasources.saving") : t("datasources.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
