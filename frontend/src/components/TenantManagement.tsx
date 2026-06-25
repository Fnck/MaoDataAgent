import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";
import type { Tenant, TenantMember } from "../types";

export default function TenantManagement() {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const user = useStore((s) => s.user);
  const fetchTenants = useStore((s) => s.fetchTenants);

  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Tenant | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const [memberModal, setMemberModal] = useState<number | null>(null);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [addUserId, setAddUserId] = useState("");

  const isAdmin = user?.role === "admin";

  const load = async () => {
    const data = await api.listTenants(token);
    setTenants(data);
  };

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <div className="p-6 text-center text-surface-400 text-sm">
        {t("tenant.adminOnly")}
      </div>
    );
  }

  const handleCreate = () => {
    setEditing(null);
    setName("");
    setDescription("");
    setShowForm(true);
  };

  const handleEdit = (t: Tenant) => {
    setEditing(t);
    setName(t.name);
    setDescription(t.description || "");
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await api.updateTenant(token, editing.id, {
          name: name.trim(),
          description: description.trim() || undefined,
        });
      } else {
        await api.createTenant(token, {
          name: name.trim(),
          description: description.trim() || undefined,
        });
      }
      setShowForm(false);
      await load();
      fetchTenants();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : t("datasources.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (tenant: Tenant) => {
    if (!confirm(t("tenant.confirmDelete", { name: tenant.name }))) return;
    await api.deleteTenant(token, tenant.id);
    await load();
    fetchTenants();
  };

  const handleManageMembers = async (tenantId: number) => {
    setMemberModal(tenantId);
    const m = await api.listTenantMembers(token, tenantId);
    setMembers(m);
    setAddUserId("");
  };

  const handleAddMember = async () => {
    if (!memberModal || !addUserId.trim()) return;
    try {
      await api.addTenantMember(token, memberModal, {
        user_id: parseInt(addUserId),
        role: "member",
      });
      const m = await api.listTenantMembers(token, memberModal);
      setMembers(m);
      setAddUserId("");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to add member");
    }
  };

  const handleRemoveMember = async (userId: number) => {
    if (!memberModal) return;
    await api.removeTenantMember(token, memberModal, userId);
    const m = await api.listTenantMembers(token, memberModal);
    setMembers(m);
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-surface-800">{t("tenant.title")}</h2>
        <button onClick={handleCreate} className="btn-primary text-sm">
          {t("tenant.create")}
        </button>
      </div>

      {tenants.length === 0 ? (
        <div className="text-center text-surface-400 text-sm py-8">
          {t("tenant.empty")}
        </div>
      ) : (
        <div className="space-y-3">
          {tenants.map((tenant) => (
            <div
              key={tenant.id}
              className="p-4 bg-white border border-surface-200 rounded-xl shadow-xs"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-surface-800">{tenant.name}</h3>
                  {tenant.description && (
                    <p className="text-sm text-surface-500 mt-0.5">{tenant.description}</p>
                  )}
                </div>
                <div className="flex gap-1.5">
                  <button
                    onClick={() => handleManageMembers(tenant.id)}
                    className="text-xs px-2.5 py-1 rounded-lg bg-surface-100 text-surface-600 hover:bg-surface-200"
                  >
                    {t("tenant.members")}
                  </button>
                  <button
                    onClick={() => handleEdit(tenant)}
                    className="text-xs px-2.5 py-1 rounded-lg bg-surface-100 text-surface-600 hover:bg-surface-200"
                  >
                    {t("datasources.edit")}
                  </button>
                  <button
                    onClick={() => handleDelete(tenant)}
                    className="text-xs px-2.5 py-1 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"
                  >
                    {t("datasources.delete")}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-2xl shadow-xl w-[400px] p-6">
            <h3 className="text-lg font-semibold text-surface-800 mb-4">
              {editing ? t("tenant.edit") : t("tenant.create")}
            </h3>
            <div className="mb-3">
              <label className="block text-sm font-medium text-surface-600 mb-1">
                {t("datasources.name")}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-surface-200 text-sm focus:outline-none focus:border-brand-400"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-surface-600 mb-1">
                {t("tenant.description")}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 rounded-xl border border-surface-200 text-sm focus:outline-none focus:border-brand-400 resize-none"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-xl text-sm text-surface-600 hover:bg-surface-100"
              >
                {t("datasources.cancel")}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !name.trim()}
                className="px-4 py-2 rounded-xl text-sm bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {saving ? t("datasources.saving") : t("datasources.save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Members Modal */}
      {memberModal !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-2xl shadow-xl w-[440px] max-h-[70vh] overflow-y-auto p-6">
            <h3 className="text-lg font-semibold text-surface-800 mb-4">
              {t("tenant.members")}
            </h3>

            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
                placeholder={t("tenant.addMemberPlaceholder")}
                className="flex-1 px-3 py-1.5 rounded-xl border border-surface-200 text-sm focus:outline-none focus:border-brand-400"
              />
              <button
                onClick={handleAddMember}
                disabled={!addUserId.trim()}
                className="px-3 py-1.5 rounded-xl text-sm bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {t("tenant.add")}
              </button>
            </div>

            {members.length === 0 ? (
              <div className="text-center text-surface-400 text-sm py-4">
                {t("tenant.noMembers")}
              </div>
            ) : (
              <div className="space-y-2">
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between p-2 bg-surface-50 rounded-xl"
                  >
                    <div>
                      <span className="text-sm font-medium text-surface-700">
                        {m.username}
                      </span>
                      <span className="ml-2 text-xs text-surface-400">
                        {m.role === "admin" ? t("tenant.roleAdmin") : t("tenant.roleMember")}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRemoveMember(m.user_id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      {t("tenant.remove")}
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end mt-4">
              <button
                onClick={() => setMemberModal(null)}
                className="px-4 py-2 rounded-xl text-sm text-surface-600 hover:bg-surface-100"
              >
                {t("datasources.cancel")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
