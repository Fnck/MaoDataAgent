import { useEffect, useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import SidebarHistory from "./SidebarHistory";
import ResourcePanel from "./ResourcePanel";
import ChatArea from "./ChatArea";
import DebugDrawer from "./DebugDrawer";
import ResetPasswordModal from "./ResetPasswordModal";

import SkillBrowser from "./SkillBrowser";

const MIN_PANEL_WIDTH = 280;
const DEFAULT_PANEL_WIDTH = 320;
const MAX_PANEL_WIDTH = 640;

export default function Layout() {
  const { t, i18n } = useTranslation();
  const fetchConversations = useStore((s) => s.fetchConversations);
  const user = useStore((s) => s.user);
  const logout = useStore((s) => s.logout);
  const leftSidebarOpen = useStore((s) => s.leftSidebarOpen);
  const resourcePanelOpen = useStore((s) => s.resourcePanelOpen);
  const toggleLeftSidebar = useStore((s) => s.toggleLeftSidebar);
  const toggleResourcePanel = useStore((s) => s.toggleResourcePanel);
  const debugDrawerOpen = useStore((s) => s.debugDrawerOpen);
  const userDatasources = useStore((s) => s.userDatasources);
  const activeDatasourceId = useStore((s) => s.activeDatasourceId);
  const fetchUserDatasources = useStore((s) => s.fetchUserDatasources);
  const currentTenantId = useStore((s) => s.currentTenantId);
  const tenants = useStore((s) => s.tenants);
  const fetchTenants = useStore((s) => s.fetchTenants);
  const switchTenant = useStore((s) => s.switchTenant);

  const [historyOpen, setHistoryOpen] = useState(true);
  const [skillsOpen, setSkillsOpen] = useState(true);
  const [showResetModal, setShowResetModal] = useState(false);

  const toggleLang = () => {
    const next = i18n.language === "zh" ? "en" : "zh";
    i18n.changeLanguage(next);
  };

  const [panelWidth, setPanelWidth] = useState(DEFAULT_PANEL_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(DEFAULT_PANEL_WIDTH);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    startXRef.current = e.clientX;
    startWidthRef.current = panelWidth;
  }, [panelWidth]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    const delta = startXRef.current - e.clientX;
    const newWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, startWidthRef.current + delta));
    setPanelWidth(newWidth);
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
  }, [isDragging]);

  useEffect(() => {
    if (!isDragging) return;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  useEffect(() => {
    fetchConversations();
    fetchUserDatasources();
    fetchTenants();
  }, [fetchConversations, fetchUserDatasources, fetchTenants]);

  return (
    <div className="h-screen flex flex-col bg-surface-50">
      {/* Top bar */}
      <div className="h-14 bg-white/80 backdrop-blur-md shadow-xs border-b border-surface-200/60 flex items-center px-5 shrink-0">
        <button
          onClick={toggleLeftSidebar}
          className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out mr-3"
          title={t("layout.toggleHistory")}
        >
          <svg className="w-5 h-5 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="font-semibold text-surface-800 text-base tracking-tight">{t("app.title")}</span>
        {tenants.length > 0 && (
          <select
            value={currentTenantId || ""}
            onChange={(e) => {
              const id = parseInt(e.target.value);
              if (id) switchTenant(id);
            }}
            className="ml-3 px-2 py-0.5 rounded-lg border border-surface-200 text-xs text-surface-600 bg-white cursor-pointer"
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        )}
        {(() => {
          const activeDs = userDatasources.find((d) => d.id === activeDatasourceId);
          if (activeDs) {
            return (
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 border border-brand-200">
                {activeDs.name}
              </span>
            );
          }
          return null;
        })()}
        <div className="flex-1" />
        {user && (
          <>
            <span className="text-sm text-surface-500 mr-3">
              {user.username}
              {user.role === "admin" && (
                <span className="ml-1.5 badge bg-semantic-warning-100 text-semantic-warning-700">
                  admin
                </span>
              )}
            </span>
            <button
              onClick={toggleLang}
              className="px-2.5 py-1 rounded-full hover:bg-surface-100 active:scale-95 text-xs font-medium text-surface-500 transition-all duration-200 ease-out mr-1 border border-surface-200/60"
              title={i18n.language === "zh" ? "Switch to English" : "切换中文"}
            >
              {i18n.language === "zh" ? "EN" : "中"}
            </button>
            {user.role === "admin" && (
              <button
                onClick={() => setShowResetModal(true)}
                className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out mr-1"
                title={t("layout.resetPassword")}
              >
                <svg className="w-4.5 h-4.5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            )}
            <button
              onClick={logout}
              className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out"
              title={t("layout.signOut")}
            >
              <svg className="w-4.5 h-4.5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
              </svg>
            </button>
          </>
        )}
        <button
          onClick={toggleResourcePanel}
          className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out ml-1"
          title={t("layout.toggleResources")}
        >
          <svg className="w-5 h-5 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V9a2 2 0 00-2-2h-2l-2-2H6a2 2 0 00-2 2z" />
          </svg>
        </button>
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        {leftSidebarOpen && (
          <div className="w-64 shadow-sm border-r border-surface-200/60 bg-white shrink-0 flex flex-col">
            {/* History Section */}
            <div className={`flex flex-col min-h-0 ${historyOpen && skillsOpen ? "flex-1" : ""}`}>
              <button
                onClick={() => setHistoryOpen(!historyOpen)}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-sm font-semibold text-surface-700 uppercase tracking-wider hover:bg-surface-50 transition-colors duration-200 shrink-0"
              >
                <svg
                  className={`w-3.5 h-3.5 text-surface-400 transition-transform duration-200 ${historyOpen ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                {t("layout.history")}
              </button>
              {historyOpen && (
                <div className={`overflow-y-auto min-h-0 ${historyOpen && skillsOpen ? "flex-1" : ""}`}>
                  <SidebarHistory />
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="border-t border-surface-200/60 shrink-0" />

            {/* Skills Section */}
            <div className={`flex flex-col min-h-0 ${historyOpen && skillsOpen ? "flex-1" : ""}`}>
              <button
                onClick={() => setSkillsOpen(!skillsOpen)}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-sm font-semibold text-surface-700 uppercase tracking-wider hover:bg-surface-50 transition-colors duration-200 shrink-0"
              >
                <svg
                  className={`w-3.5 h-3.5 text-surface-400 transition-transform duration-200 ${skillsOpen ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                {t("layout.skills")}
              </button>
              {skillsOpen && (
                <div className={`overflow-y-auto min-h-0 ${historyOpen && skillsOpen ? "flex-1" : ""}`}>
                  <SkillBrowser />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatArea />
        </div>

        {/* Right resource panel */}
        {resourcePanelOpen && (
          <div className="flex shrink-0" style={{ width: panelWidth }}>
            {/* Drag handle */}
            <div
              onMouseDown={handleMouseDown}
              className={`w-1.5 cursor-col-resize rounded-full transition-colors duration-200 ${
                isDragging ? "bg-brand-500" : "bg-transparent hover:bg-brand-300"
              }`}
            />
            <div className="flex-1 border-l border-surface-200/60 bg-white overflow-y-auto">
              <ResourcePanel />
            </div>
          </div>
        )}
      </div>

      {/* Debug drawer overlay */}
      {debugDrawerOpen && <DebugDrawer />}

      {/* Reset password modal */}
      {showResetModal && <ResetPasswordModal onClose={() => setShowResetModal(false)} />}
    </div>
  );
}
