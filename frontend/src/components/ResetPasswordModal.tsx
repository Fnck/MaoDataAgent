import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";

interface Props {
  onClose: () => void;
}

export default function ResetPasswordModal({ onClose }: Props) {
  const { t } = useTranslation();
  const token = useStore((s) => s.token);
  const [targetUsername, setTargetUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const res = await api.resetPassword(token!, targetUsername, newPassword);
      setSuccess(res.message);
      setTargetUsername("");
      setNewPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("resetPassword.failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-surface-900/30 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white p-8 rounded-3xl shadow-glass w-[380px] animate-scale-in">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-semibold text-surface-800">{t("resetPassword.title")}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out"
          >
            <svg className="w-5 h-5 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="bg-semantic-danger-50 text-semantic-danger-700 text-sm p-3 rounded-xl mb-4 animate-fade-in">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-semantic-success-50 text-semantic-success-700 text-sm p-3 rounded-xl mb-4 animate-fade-in">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-surface-700 mb-1.5">
              {t("resetPassword.username")}
            </label>
            <input
              type="text"
              value={targetUsername}
              onChange={(e) => setTargetUsername(e.target.value)}
              className="input"
              required
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-surface-700 mb-1.5">
              {t("resetPassword.newPassword")}
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input"
              required
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1 py-2.5"
            >
              {t("resetPassword.cancel")}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex-1 py-2.5"
            >
              {loading ? t("resetPassword.resetting") : t("resetPassword.reset")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
