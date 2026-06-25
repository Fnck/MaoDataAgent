import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import ActivityForm from "./ActivityForm";
import ObjectForm from "./ObjectForm";
import RuleForm from "./RuleForm";
import MetricForm from "./MetricForm";
import ActivityFlowChart from "./ActivityFlowChart";
import type {
  BusinessActivity,
  BusinessObject,
  BusinessRule,
  Metric,
} from "../types";

type SubTab = "activities" | "objects" | "rules" | "metrics";
type ActivitiesView = "list" | "flow";

export default function OntologyManagement({ compact = false, datasourceName = "" }: { compact?: boolean; datasourceName?: string }) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const activities = useStore((s) => s.activities);
  const objects = useStore((s) => s.objects);
  const rules = useStore((s) => s.rules);
  const metrics = useStore((s) => s.metrics);
  const fetchActivities = useStore((s) => s.fetchActivities);
  const fetchObjects = useStore((s) => s.fetchObjects);
  const fetchRules = useStore((s) => s.fetchRules);
  const fetchMetrics = useStore((s) => s.fetchMetrics);

  const [activeSubTab, setActiveSubTab] = useState<SubTab>("activities");
  const [activitiesView, setActivitiesView] = useState<ActivitiesView>("flow");
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<BusinessActivity | BusinessObject | BusinessRule | Metric | null>(null);

  // Re-fetch when datasource changes
  useEffect(() => {
    if (datasourceName) {
      fetchActivities();
      fetchObjects();
      fetchRules();
      fetchMetrics();
    }
  }, [datasourceName, fetchActivities, fetchObjects, fetchRules, fetchMetrics]);

  const handleEdit = (item: BusinessActivity | BusinessObject | BusinessRule | Metric) => {
    setEditingItem(item);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingItem(null);
  };

  const handleFormSaved = () => {
    handleCloseForm();
    if (activeSubTab === "activities") fetchActivities();
    else if (activeSubTab === "objects") fetchObjects();
    else if (activeSubTab === "rules") fetchRules();
    else fetchMetrics();
  };

  const subtabs: { key: SubTab; label: string }[] = [
    { key: "activities", label: t("ontology.activities") },
    { key: "objects", label: t("ontology.businessObjects") },
    { key: "rules", label: t("ontology.rules") },
    { key: "metrics", label: t("ontology.metrics") },
  ];

  const renderSubTabContent = () => {
    switch (activeSubTab) {
      case "activities":
        if (activitiesView === "flow") {
          return (
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-semibold text-surface-700">{t("ontology.businessActivitiesFlow")}</h3>
                  <div className="flex bg-surface-100 rounded-xl p-1">
                    <button
                      onClick={() => setActivitiesView("flow")}
                      className="px-2.5 py-1 text-sm rounded-lg bg-white text-brand-600 shadow-xs font-medium transition-all duration-200 ease-out"
                    >
                      {t("ontology.flow")}
                    </button>
                    <button
                      onClick={() => setActivitiesView("list")}
                      className="px-2.5 py-1 text-sm rounded-lg text-surface-500 hover:text-surface-700 transition-all duration-200 ease-out"
                    >
                      {t("ontology.list")}
                    </button>
                  </div>
                </div>
              </div>
              <ActivityFlowChart
                activities={activities}
                onEdit={(act) => {
                  setEditingItem(act);
                  setShowForm(true);
                }}
                onDelete={async (act) => {
                  await api.deleteActivity(token, act.activity_id);
                  fetchActivities();
                }}
                onAdd={() => {
                  setEditingItem(null);
                  setShowForm(true);
                }}
              />
            </div>
          );
        }
        return (
          <div>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold text-surface-700">{t("ontology.businessActivities")}</h3>
                <div className="flex bg-surface-100 rounded-xl p-1">
                    <button
                      onClick={() => setActivitiesView("flow")}
                      className="px-2.5 py-1 text-sm rounded-lg text-surface-500 hover:text-surface-700 transition-all duration-200 ease-out"
                    >
                      {t("ontology.flow")}
                    </button>
                    <button
                      onClick={() => setActivitiesView("list")}
                      className="px-2.5 py-1 text-sm rounded-lg bg-white text-brand-600 shadow-xs font-medium transition-all duration-200 ease-out"
                    >
                    {t("ontology.list")}
                  </button>
                </div>
              </div>
              <button
                onClick={() => { setEditingItem(null); setShowForm(true); }}
                className="btn-primary text-sm"
              >
                {t("ontology.addActivity")}
              </button>
            </div>
            {activities.length === 0 ? (
              <p className="text-sm text-surface-400">{t("ontology.noActivities")}</p>
            ) : (
              <div className="space-y-3">
                {activities.map((act) => (
                  <div
                    key={act.activity_id}
                    className="card-hover p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-semibold text-surface-800">{act.name}</p>
                        {act.description && (
                          <p className="text-sm text-surface-500 mt-1 line-clamp-2">
                            {act.description}
                          </p>
                        )}
                        {act.pre_activities && (
                          <p className="text-xs text-surface-400 mt-1.5">
                            {t("ontology.pre")}: {act.pre_activities}
                          </p>
                        )}
                        {act.post_activities && (
                          <p className="text-xs text-surface-400">
                            {t("ontology.post")}: {act.post_activities}
                          </p>
                        )}
                        {act.operated_objects && (
                          <p className="text-xs text-surface-400">
                            {t("ontology.objects")}: {act.operated_objects}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0 ml-3">
                        <button
                          onClick={() => handleEdit(act)}
                          className="text-sm text-brand-500 font-medium hover:text-brand-700 transition-colors"
                        >
                          {t("ontology.edit")}
                        </button>
                        <button
                          onClick={async () => {
                            await api.deleteActivity(token, act.activity_id);
                            fetchActivities();
                          }}
                          className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 transition-colors"
                        >
                          {t("ontology.delete")}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case "objects":
        return (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-surface-700">{t("ontology.businessObjects")}</h3>
              <button
                onClick={() => { setEditingItem(null); setShowForm(true); }}
                className="btn-primary text-sm"
              >
                {t("ontology.addObject")}
              </button>
            </div>
            {objects.length === 0 ? (
              <p className="text-sm text-surface-400">{t("ontology.noObjects")}</p>
            ) : (
              <div className="space-y-3">
                {objects.map((obj) => (
                  <div
                    key={obj.object_id}
                    className="card-hover p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-semibold text-surface-800">{obj.name}</p>
                        {obj.description && (
                          <p className="text-sm text-surface-500 mt-1 line-clamp-2">
                            {obj.description}
                          </p>
                        )}
                        {obj.related_entities && (
                          <p className="text-xs text-surface-400 mt-1.5">
                            {t("ontology.entities")}: {obj.related_entities}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0 ml-3">
                        <button
                          onClick={() => handleEdit(obj)}
                          className="text-sm text-brand-500 font-medium hover:text-brand-700 transition-colors"
                        >
                          {t("ontology.edit")}
                        </button>
                        <button
                          onClick={async () => {
                            await api.deleteObject(token, obj.object_id);
                            fetchObjects();
                          }}
                          className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 transition-colors"
                        >
                          {t("ontology.delete")}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case "rules":
        return (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-surface-700">{t("ontology.rules")}</h3>
              <button
                onClick={() => { setEditingItem(null); setShowForm(true); }}
                className="btn-primary text-sm"
              >
                {t("ontology.addRule")}
              </button>
            </div>
            {rules.length === 0 ? (
              <p className="text-sm text-surface-400">{t("ontology.noRules")}</p>
            ) : (
              <div className="space-y-3">
                {rules.map((rule) => (
                  <div
                    key={rule.rule_id}
                    className="card-hover p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-surface-800">{rule.name}</p>
                          {rule.status && (
                            <span className={`badge ${
                              rule.status === "enabled" ? "bg-semantic-success-50 text-semantic-success-700" : "bg-surface-100 text-surface-500"
                            }`}>
                              {rule.status}
                            </span>
                          )}
                        </div>
                        {rule.description && (
                          <p className="text-sm text-surface-500 mt-1">{rule.description}</p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0 ml-3">
                        <button
                          onClick={() => handleEdit(rule)}
                          className="text-sm text-brand-500 font-medium hover:text-brand-700 transition-colors"
                        >
                          {t("ontology.edit")}
                        </button>
                        <button
                          onClick={async () => {
                            await api.deleteRule(token, rule.rule_id);
                            fetchRules();
                          }}
                          className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 transition-colors"
                        >
                          {t("ontology.delete")}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case "metrics":
        return (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-surface-700">{t("ontology.metrics")}</h3>
              <button
                onClick={() => { setEditingItem(null); setShowForm(true); }}
                className="btn-primary text-sm"
              >
                {t("ontology.addMetric")}
              </button>
            </div>
            {metrics.length === 0 ? (
              <p className="text-sm text-surface-400">{t("ontology.noMetrics")}</p>
            ) : (
              <div className="space-y-3">
                {metrics.map((m) => (
                  <div
                    key={m.metric_id}
                    className="card-hover p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-semibold text-surface-800">{m.name}</p>
                        {m.business_meaning && (
                          <p className="text-sm text-surface-500 mt-1 line-clamp-2">
                            {m.business_meaning}
                          </p>
                        )}
                        {m.calculation_formula && (
                          <p className="text-xs text-surface-400 mt-1.5 font-mono">
                            {m.calculation_formula}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0 ml-3">
                        <button
                          onClick={() => handleEdit(m)}
                          className="text-sm text-brand-500 font-medium hover:text-brand-700 transition-colors"
                        >
                          {t("ontology.edit")}
                        </button>
                        <button
                          onClick={async () => {
                            await api.deleteMetric(token, m.metric_id);
                            fetchMetrics();
                          }}
                          className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 transition-colors"
                        >
                          {t("ontology.delete")}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Sub-tab navigation */}
      <div className="bg-white px-3 py-2 shrink-0">
        <div className="flex gap-1">
          {subtabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveSubTab(tab.key)}
              className={activeSubTab === tab.key ? "tab-active" : "tab-inactive"}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className={`flex-1 overflow-y-auto ${compact ? "p-3" : "p-5"}`}>
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
        <div className={compact ? "" : "max-w-4xl mx-auto"}>
          {renderSubTabContent()}
        </div>
      </div>

      {/* Form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-surface-900/30 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in">
          <div className="bg-white rounded-3xl p-8 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-glass animate-scale-in">
            {activeSubTab === "activities" && (
              <ActivityForm
                editingItem={editingItem as BusinessActivity | null}
                onSaved={handleFormSaved}
                onCancel={handleCloseForm}
              />
            )}
            {activeSubTab === "objects" && (
              <ObjectForm
                editingItem={editingItem as BusinessObject | null}
                onSaved={handleFormSaved}
                onCancel={handleCloseForm}
              />
            )}
            {activeSubTab === "rules" && (
              <RuleForm
                editingItem={editingItem as BusinessRule | null}
                onSaved={handleFormSaved}
                onCancel={handleCloseForm}
              />
            )}
            {activeSubTab === "metrics" && (
              <MetricForm
                editingItem={editingItem as Metric | null}
                onSaved={handleFormSaved}
                onCancel={handleCloseForm}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
