import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { BusinessActivity } from "../types";

interface Props {
  editingItem: BusinessActivity | null;
  onSaved: () => void;
  onCancel: () => void;
}

export default function ActivityForm({ editingItem, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const isEdit = !!editingItem;

  const [name, setName] = useState(editingItem?.name || "");
  const [description, setDescription] = useState(editingItem?.description || "");
  const [preActivities, setPreActivities] = useState(editingItem?.pre_activities || "");
  const [postActivities, setPostActivities] = useState(editingItem?.post_activities || "");
  const [operatedObjects, setOperatedObjects] = useState(editingItem?.operated_objects || "");
  const [inputEntities, setInputEntities] = useState(editingItem?.input_entities || "");
  const [outputEntities, setOutputEntities] = useState(editingItem?.output_entities || "");
  const [nodeMetrics, setNodeMetrics] = useState(editingItem?.node_metrics || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isEdit && editingItem) {
        await api.updateActivity(token, editingItem.activity_id, {
          name: name.trim(),
          description: description.trim() || undefined,
          pre_activities: preActivities.trim() || undefined,
          post_activities: postActivities.trim() || undefined,
          operated_objects: operatedObjects.trim() || undefined,
          input_entities: inputEntities.trim() || undefined,
          output_entities: outputEntities.trim() || undefined,
          node_metrics: nodeMetrics.trim() || undefined,
        });
      } else {
        await api.createActivity(token, {
          name: name.trim(),
          description: description.trim() || null,
          pre_activities: preActivities.trim() || null,
          post_activities: postActivities.trim() || null,
          operated_objects: operatedObjects.trim() || null,
          input_entities: inputEntities.trim() || null,
          output_entities: outputEntities.trim() || null,
          node_metrics: nodeMetrics.trim() || null,
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
        {isEdit ? t("activityForm.editTitle") : t("activityForm.newTitle")}
      </h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder={t("activityForm.namePlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.description")}</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="input resize-none"
            placeholder={t("activityForm.descriptionPlaceholder")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.preActivities")}</label>
            <input
              value={preActivities}
              onChange={(e) => setPreActivities(e.target.value)}
              className="input"
              placeholder={t("activityForm.preActivitiesPlaceholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.postActivities")}</label>
            <input
              value={postActivities}
              onChange={(e) => setPostActivities(e.target.value)}
              className="input"
              placeholder={t("activityForm.postActivitiesPlaceholder")}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.operatedObjects")}</label>
          <input
            value={operatedObjects}
            onChange={(e) => setOperatedObjects(e.target.value)}
            className="input"
            placeholder={t("activityForm.operatedObjectsPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.inputEntities")}</label>
          <input
            value={inputEntities}
            onChange={(e) => setInputEntities(e.target.value)}
            className="input"
            placeholder={t("activityForm.inputEntitiesPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.outputEntities")}</label>
          <input
            value={outputEntities}
            onChange={(e) => setOutputEntities(e.target.value)}
            className="input"
            placeholder={t("activityForm.outputEntitiesPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("activityForm.nodeMetrics")}</label>
          <input
            value={nodeMetrics}
            onChange={(e) => setNodeMetrics(e.target.value)}
            className="input"
            placeholder={t("activityForm.nodeMetricsPlaceholder")}
          />
        </div>
      </div>
      <div className="flex justify-end gap-3 mt-8">
        <button
          onClick={onCancel}
          className="btn-secondary"
        >
          {t("activityForm.cancel")}
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="btn-primary"
        >
          {saving ? t("activityForm.saving") : isEdit ? t("activityForm.update") : t("activityForm.create")}
        </button>
      </div>
    </div>
  );
}
