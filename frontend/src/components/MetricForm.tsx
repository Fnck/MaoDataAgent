import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { Metric } from "../types";

interface Props {
  editingItem: Metric | null;
  onSaved: () => void;
  onCancel: () => void;
}

export default function MetricForm({ editingItem, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const isEdit = !!editingItem;

  const [name, setName] = useState(editingItem?.name || "");
  const [businessMeaning, setBusinessMeaning] = useState(editingItem?.business_meaning || "");
  const [calculationFormula, setCalculationFormula] = useState(editingItem?.calculation_formula || "");
  const [queryLogic, setQueryLogic] = useState(editingItem?.query_logic || "");
  const [unit, setUnit] = useState(editingItem?.unit || "");
  const [dataSource, setDataSource] = useState(editingItem?.data_source || "");
  const [refreshCycle, setRefreshCycle] = useState(editingItem?.refresh_cycle || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isEdit && editingItem) {
        await api.updateMetric(token, editingItem.metric_id, {
          name: name.trim(),
          business_meaning: businessMeaning.trim() || undefined,
          calculation_formula: calculationFormula.trim() || undefined,
          query_logic: queryLogic.trim() || undefined,
          unit: unit.trim() || undefined,
          data_source: dataSource.trim() || undefined,
          refresh_cycle: refreshCycle.trim() || undefined,
        });
      } else {
        await api.createMetric(token, {
          name: name.trim(),
          business_meaning: businessMeaning.trim() || null,
          calculation_formula: calculationFormula.trim() || null,
          query_logic: queryLogic.trim() || null,
          unit: unit.trim() || null,
          data_source: dataSource.trim() || null,
          refresh_cycle: refreshCycle.trim() || null,
          created_by: null,
          updated_by: null,
        });
      }
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-5 text-surface-800">
        {isEdit ? t("metricForm.editTitle") : t("metricForm.newTitle")}
      </h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder={t("metricForm.namePlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.businessMeaning")}</label>
          <textarea
            value={businessMeaning}
            onChange={(e) => setBusinessMeaning(e.target.value)}
            rows={2}
            className="input resize-none"
            placeholder={t("metricForm.businessMeaningPlaceholder")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.unit")}</label>
            <input
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="input"
              placeholder={t("metricForm.unitPlaceholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.refreshCycle")}</label>
            <input
              value={refreshCycle}
              onChange={(e) => setRefreshCycle(e.target.value)}
              className="input"
              placeholder={t("metricForm.refreshCyclePlaceholder")}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.calculationFormula")}</label>
          <textarea
            value={calculationFormula}
            onChange={(e) => setCalculationFormula(e.target.value)}
            rows={2}
            className="input resize-none font-mono"
            placeholder={t("metricForm.calculationFormulaPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.queryLogic")}</label>
          <textarea
            value={queryLogic}
            onChange={(e) => setQueryLogic(e.target.value)}
            rows={4}
            className="input resize-none font-mono"
            placeholder={t("metricForm.queryLogicPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("metricForm.dataSource")}</label>
          <input
            value={dataSource}
            onChange={(e) => setDataSource(e.target.value)}
            className="input"
            placeholder={t("metricForm.dataSourcePlaceholder")}
          />
        </div>
      </div>
      <div className="flex justify-end gap-3 mt-8">
        <button
          onClick={onCancel}
          className="btn-secondary"
        >
          {t("metricForm.cancel")}
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="btn-primary"
        >
          {saving ? t("metricForm.saving") : isEdit ? t("metricForm.update") : t("metricForm.create")}
        </button>
      </div>
    </div>
  );
}
