import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { BusinessObject } from "../types";

interface Props {
  editingItem: BusinessObject | null;
  onSaved: () => void;
  onCancel: () => void;
}

export default function ObjectForm({ editingItem, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const isEdit = !!editingItem;

  const [name, setName] = useState(editingItem?.name || "");
  const [description, setDescription] = useState(editingItem?.description || "");
  const [relatedEntities, setRelatedEntities] = useState(editingItem?.related_entities || "");
  const [entityRelationships, setEntityRelationships] = useState(editingItem?.entity_relationships || "");
  const [maintainer, setMaintainer] = useState(editingItem?.maintainer || "");
  const [department, setDepartment] = useState(editingItem?.department || "");
  const [permissions, setPermissions] = useState(editingItem?.permissions || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isEdit && editingItem) {
        await api.updateObject(token, editingItem.object_id, {
          name: name.trim(),
          description: description.trim() || undefined,
          related_entities: relatedEntities.trim() || undefined,
          entity_relationships: entityRelationships.trim() || undefined,
          maintainer: maintainer.trim() || undefined,
          department: department.trim() || undefined,
          permissions: permissions.trim() || undefined,
        });
      } else {
        await api.createObject(token, {
          name: name.trim(),
          description: description.trim() || null,
          related_entities: relatedEntities.trim() || null,
          entity_relationships: entityRelationships.trim() || null,
          maintainer: maintainer.trim() || null,
          department: department.trim() || null,
          permissions: permissions.trim() || null,
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
        {isEdit ? t("objectForm.editTitle") : t("objectForm.newTitle")}
      </h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder={t("objectForm.namePlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.description")}</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="input resize-none"
            placeholder={t("objectForm.descriptionPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.relatedEntities")}</label>
          <input
            value={relatedEntities}
            onChange={(e) => setRelatedEntities(e.target.value)}
            className="input"
            placeholder={t("objectForm.relatedEntitiesPlaceholder")}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.entityRelationships")}</label>
          <textarea
            value={entityRelationships}
            onChange={(e) => setEntityRelationships(e.target.value)}
            rows={2}
            className="input resize-none"
            placeholder={t("objectForm.entityRelationshipsPlaceholder")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.maintainer")}</label>
            <input
              value={maintainer}
              onChange={(e) => setMaintainer(e.target.value)}
              className="input"
              placeholder={t("objectForm.maintainerPlaceholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.department")}</label>
            <input
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="input"
              placeholder={t("objectForm.departmentPlaceholder")}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-700 mb-1.5">{t("objectForm.permissions")}</label>
          <input
            value={permissions}
            onChange={(e) => setPermissions(e.target.value)}
            className="input"
            placeholder={t("objectForm.permissionsPlaceholder")}
          />
        </div>
      </div>
      <div className="flex justify-end gap-3 mt-8">
        <button
          onClick={onCancel}
          className="btn-secondary"
        >
          {t("objectForm.cancel")}
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="btn-primary"
        >
          {saving ? t("objectForm.saving") : isEdit ? t("objectForm.update") : t("objectForm.create")}
        </button>
      </div>
    </div>
  );
}
