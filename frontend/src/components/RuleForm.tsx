import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { BusinessRule } from "../types";

interface Props {
  editingItem: BusinessRule | null;
  onSaved: () => void;
  onCancel: () => void;
}

export default function RuleForm({ editingItem, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const isEdit = !!editingItem;

  const [name, setName] = useState(editingItem?.name || "");
  const [description, setDescription] = useState(editingItem?.description || "");
  const [category, setCategory] = useState(editingItem?.category || "");
  const [conditionExpression, setConditionExpression] = useState(editingItem?.condition_expression || "");
  const [associatedActivityId, setAssociatedActivityId] = useState(editingItem?.associated_activity_id?.toString() || "");
  const [associatedObjectId, setAssociatedObjectId] = useState(editingItem?.associated_object_id?.toString() || "");
  const [priority, setPriority] = useState(editingItem?.priority?.toString() || "");
  const [status, setStatus] = useState(editingItem?.status || "enabled");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        name: name.trim(),
        description: description.trim() || null,
        category: category.trim() || null,
        condition_expression: conditionExpression.trim() || null,
        associated_activity_id: associatedActivityId ? parseInt(associatedActivityId) : null,
        associated_object_id: associatedObjectId ? parseInt(associatedObjectId) : null,
        priority: priority ? parseInt(priority) : null,
        status,
      };
      if (isEdit && editingItem) {
        await api.updateRule(token, editingItem.rule_id, data);
      } else {
        await api.createRule(token, {
          ...data,
          created_by: null,
          updated_by: null,
        } as unknown as Omit<BusinessRule, "rule_id" | "created_time" | "updated_time">);
      }
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-5 text-surface-800">
        {isEdit ? t("ruleForm.editTitle") : t("ruleForm.newTitle")}
      </h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder={t("ruleForm.namePlaceholder")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.category")}</label>
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input"
              placeholder={t("ruleForm.categoryPlaceholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.status")}</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="input"
            >
              <option value="enabled">{t("ruleForm.enabled")}</option>
              <option value="disabled">{t("ruleForm.disabled")}</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.description")}</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="input resize-none"
            placeholder={t("ruleForm.descriptionPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.conditionExpression")}</label>
          <textarea
            value={conditionExpression}
            onChange={(e) => setConditionExpression(e.target.value)}
            rows={3}
            className="input resize-none font-mono"
            placeholder={t("ruleForm.conditionExpressionPlaceholder")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.associatedActivityId")}</label>
            <input
              value={associatedActivityId}
              onChange={(e) => setAssociatedActivityId(e.target.value)}
              className="input"
              placeholder={t("ruleForm.associatedActivityIdPlaceholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.associatedObjectId")}</label>
            <input
              value={associatedObjectId}
              onChange={(e) => setAssociatedObjectId(e.target.value)}
              className="input"
              placeholder={t("ruleForm.associatedObjectIdPlaceholder")}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("ruleForm.priority")}</label>
          <input
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            type="number"
            className="input"
            placeholder={t("ruleForm.priorityPlaceholder")}
          />
        </div>
      </div>
      <div className="flex justify-end gap-3 mt-8">
        <button
          onClick={onCancel}
          className="btn-secondary"
        >
          {t("ruleForm.cancel")}
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="btn-primary"
        >
          {saving ? t("ruleForm.saving") : isEdit ? t("ruleForm.update") : t("ruleForm.create")}
        </button>
      </div>
    </div>
  );
}
