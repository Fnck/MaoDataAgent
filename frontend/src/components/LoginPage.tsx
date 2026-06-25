import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";

export default function LoginPage() {
  const { t } = useTranslation();
  const login = useStore((s) => s.login);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("login.loginFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900 items-center justify-center overflow-hidden">
        {/* Decorative blurred circles */}
        <div className="absolute top-20 left-20 w-72 h-72 bg-brand-400/30 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-brand-300/20 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/3 w-48 h-48 bg-white/10 rounded-full blur-2xl" />
        <div className="relative z-10 text-center px-12">
          <h1 className="text-6xl font-bold text-white mb-4 tracking-tight">DataAgent</h1>
          <p className="text-brand-200 text-lg font-light max-w-md mx-auto leading-relaxed">
            {t("login.heroSubtitle")}
          </p>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center bg-surface-50 p-6">
        <form
          onSubmit={handleSubmit}
          className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-glass p-10 w-full max-w-sm animate-scale-in border border-white/20"
        >
          {/* Mobile-only title */}
          <div className="lg:hidden text-center mb-6">
            <h1 className="text-hero font-bold gradient-text mb-2">DataAgent</h1>
            <p className="text-surface-500 text-sm">{t("login.heroSubtitle")}</p>
          </div>

          <h2 className="text-2xl font-semibold text-surface-800 mb-1 hidden lg:block">
            {t("login.signIn")}
          </h2>
          <p className="text-surface-500 text-sm mb-8 hidden lg:block">
            {t("login.heroSubtitle")}
          </p>

          {error && (
            <div className="bg-semantic-danger-50 text-semantic-danger-700 text-sm p-3 rounded-xl mb-5 animate-fade-in">
              {error}
            </div>
          )}

          <div className="mb-5">
            <label className="block text-sm font-medium text-surface-700 mb-1.5">
              {t("login.username")}
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input"
              required
            />
          </div>

          <div className="mb-8">
            <label className="block text-sm font-medium text-surface-700 mb-1.5">
              {t("login.password")}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 text-sm"
          >
            {loading ? t("login.signingIn") : t("login.signIn")}
          </button>
        </form>
      </div>
    </div>
  );
}
