import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import OntologyManagement from "./OntologyManagement";
import DataAssetsManagement from "./DataAssetsManagement";

type Tab = "management" | "assets";

export default function OntologyPage() {
  const { t } = useTranslation();
  const setDatasourceSubTab = useStore((s) => s.setDatasourceSubTab);
  const fetchActivities = useStore((s) => s.fetchActivities);
  const fetchObjects = useStore((s) => s.fetchObjects);
  const fetchRules = useStore((s) => s.fetchRules);
  const fetchMetrics = useStore((s) => s.fetchMetrics);
  const fetchDataAssets = useStore((s) => s.fetchDataAssets);
  const fetchObjectRelationships = useStore((s) => s.fetchObjectRelationships);

  const [activeTab, setActiveTab] = useState<Tab>("management");

  useEffect(() => {
    fetchActivities();
    fetchObjects();
    fetchRules();
    fetchMetrics();
    fetchDataAssets();
    fetchObjectRelationships();
  }, [
    fetchActivities,
    fetchObjects,
    fetchRules,
    fetchMetrics,
    fetchDataAssets,
    fetchObjectRelationships,
  ]);

  return (
    <div className="h-screen flex flex-col bg-surface-50">
      {/* Top bar */}
      <div className="h-14 bg-white/80 backdrop-blur-md shadow-xs border-b border-surface-200/60 flex items-center px-5 shrink-0">
        <button
          onClick={() => setDatasourceSubTab("connections")}
          className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out mr-3"
          title={t("ontologyPage.backToChat")}
        >
          <svg className="w-5 h-5 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="font-semibold text-surface-800 text-base tracking-tight">{t("ontologyPage.title")}</span>
        <div className="flex-1" />

        {/* Tab navigation - pill style */}
        <div className="flex bg-surface-100 rounded-xl p-1">
          <button
            onClick={() => setActiveTab("management")}
            className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-all duration-200 ease-out ${
              activeTab === "management"
                ? "bg-white text-brand-600 shadow-xs"
                : "text-surface-500 hover:text-surface-700"
            }`}
          >
            {t("ontologyPage.ontologyManagement")}
          </button>
          <button
            onClick={() => setActiveTab("assets")}
            className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-all duration-200 ease-out ${
              activeTab === "assets"
                ? "bg-white text-brand-600 shadow-xs"
                : "text-surface-500 hover:text-surface-700"
            }`}
          >
            {t("ontologyPage.dataAssets")}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "management" ? <OntologyManagement /> : <DataAssetsManagement />}
      </div>
    </div>
  );
}
