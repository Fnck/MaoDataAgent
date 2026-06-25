import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { DebugEvent, DebugCategory } from "../types";

const CATEGORY_KEYS: Record<DebugCategory, { icon: React.ReactNode; color: string; bgColor: string; labelKey: string }> = {
  llm_call: {
    icon: <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>,
    color: "text-semantic-info-700",
    bgColor: "bg-semantic-info-50 border-semantic-info-100",
    labelKey: "debug.llmCall",
  },
  tool_call: {
    icon: <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.1 5.1a2.121 2.121 0 01-3-3l5.1-5.1m0 0L14.5 7.07a2.121 2.121 0 013 3l-3.08 3.08M11.42 15.17l3.08-3.08" /></svg>,
    color: "text-semantic-purple-700",
    bgColor: "bg-semantic-purple-50 border-semantic-purple-100",
    labelKey: "debug.toolCall",
  },
  context: {
    icon: <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" /></svg>,
    color: "text-semantic-success-700",
    bgColor: "bg-semantic-success-50 border-semantic-success-100",
    labelKey: "debug.context",
  },
  system: {
    icon: <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
    color: "text-surface-700",
    bgColor: "bg-surface-50 border-surface-200",
    labelKey: "debug.system",
  },
};

function buildSummary(event: DebugEvent): string {
  const d = event.data;
  switch (event.category) {
    case "llm_call":
      return `${d.model || "?"} | ${d.duration_ms ?? "?"}ms | tokens: ${(d.usage as Record<string, unknown>)?.total_tokens ?? "?"}`;
    case "tool_call":
      return `${d.tool_name || "?"}${d.error ? " (error)" : ""} | ${d.duration_ms ?? "?"}ms`;
    case "context":
      return `${(d.selected_files as unknown[])?.length ?? 0} files, ${(d.selected_tables as unknown[])?.length ?? 0} tables`;
    case "system":
      return `${d.message || ""}`;
    default:
      return "";
  }
}

export default function DebugCard({ event }: { event: DebugEvent }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const config = CATEGORY_KEYS[event.category] || CATEGORY_KEYS.system;
  const summary = buildSummary(event);

  return (
    <div className={`my-px border rounded-md shadow-xs hover:shadow-sm transition-all duration-200 ease-out ${config.bgColor}`}>
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 px-1.5 py-0.5 cursor-pointer text-[10px] leading-tight"
      >
        <span className={config.color}>{config.icon}</span>
        <span className={`font-medium ${config.color}`}>{t(config.labelKey)}</span>
        <span className="text-surface-500 truncate flex-1">{summary}</span>
        <span className="text-surface-400 text-[9px]">
          #{event.seq}
        </span>
        <span className="text-surface-400 text-[9px]">
          {new Date(event.timestamp).toLocaleTimeString()}
        </span>
        <svg
          className={`w-2.5 h-2.5 text-surface-400 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
      {expanded && (
        <div className="px-1.5 pb-1 border-t border-surface-200/40">
          <pre className="text-[9px] text-surface-600 whitespace-pre-wrap break-all bg-white/50 p-1.5 rounded-md mt-0.5 max-h-40 overflow-y-auto font-mono leading-tight">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
