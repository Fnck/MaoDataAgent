import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import DebugCard from "./DebugCard";
import type { DebugEvent } from "../types";

export default function DebugDrawer() {
  const { t } = useTranslation();
  const debugEvents = useStore((s) => s.debugEvents);
  const messages = useStore((s) => s.messages);
  const closeDebugDrawer = useStore((s) => s.closeDebugDrawer);
  const [copied, setCopied] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const filteredEvents =
    filter === "all"
      ? debugEvents
      : debugEvents.filter((e) => e.category === filter);

  // Group events by message_id for display, sorted by seq
  const eventsByMessage = new Map<number | null, DebugEvent[]>();
  for (const evt of filteredEvents.sort((a, b) => {
    return (parseInt(a.seq, 10) || 0) - (parseInt(b.seq, 10) || 0);
  })) {
    const key = evt.message_id;
    if (!eventsByMessage.has(key)) {
      eventsByMessage.set(key, []);
    }
    eventsByMessage.get(key)!.push(evt);
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(debugEvents, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Find message content by id
  const getMessageContent = (msgId: number | null): string => {
    if (msgId === null) return t("debug.preStream");
    const msg = messages.find((m) => m.id === msgId);
    if (!msg) return `Message #${msgId}`;
    const preview = msg.content.slice(0, 80);
    return msg.role === "assistant"
      ? `${t("debug.assistant")}: ${preview}${msg.content.length > 80 ? "..." : ""}`
      : `${t("debug.user")}: ${preview}${msg.content.length > 80 ? "..." : ""}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-surface-900/30 backdrop-blur-sm" onClick={closeDebugDrawer} />

      {/* Drawer */}
      <div className="relative w-[520px] bg-white/90 backdrop-blur-xl shadow-glass overflow-y-auto flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="sticky top-0 bg-white/80 backdrop-blur-md border-b border-surface-200/60 px-5 py-3.5 flex items-center z-10">
          <h2 className="font-semibold text-surface-800">{t("debug.title")}</h2>
          <span className="ml-2 text-xs text-surface-400">({debugEvents.length})</span>
          <div className="flex-1" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="text-sm border border-surface-200/60 rounded-lg px-2 py-1.5 mr-3 text-surface-600 bg-white focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            <option value="all">{t("debug.all")}</option>
            <option value="llm_call">{t("debug.llmCall")}</option>
            <option value="tool_call">{t("debug.toolCall")}</option>
            <option value="context">{t("debug.context")}</option>
            <option value="system">{t("debug.system")}</option>
          </select>
          <button
            onClick={handleCopy}
            className="text-sm text-brand-500 hover:text-brand-700 font-medium mr-3 transition-colors"
          >
            {copied ? t("debug.copied") : t("debug.copyJson")}
          </button>
          <button
            onClick={closeDebugDrawer}
            className="p-2 rounded-xl hover:bg-surface-100 active:scale-95 transition-all duration-200 ease-out"
          >
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        {filteredEvents.length === 0 ? (
          <div className="p-6 text-center text-surface-400 text-sm">
            {t("debug.noEvents")}
          </div>
        ) : (
          <div className="p-5 space-y-5">
            {Array.from(eventsByMessage.entries()).map(([msgId, events]) => (
              <div key={msgId ?? "null"}>
                <div className="text-sm font-medium text-surface-500 mb-2 truncate">
                  {getMessageContent(msgId)}
                </div>
                <div className="space-y-0.5">
                  {events.map((evt) => (
                    <DebugCard key={`drawer-debug-${evt.event_id}`} event={evt} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
