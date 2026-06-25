import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";

export default function WorkflowPanel() {
  const { t } = useTranslation();
  const workflowSteps = useStore((s) => s.workflowSteps);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const toggleExpand = (stepId: number) => {
    setExpandedSteps((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
  };

  if (workflowSteps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-surface-400 text-sm">
        <svg className="w-8 h-8 mb-2 text-surface-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
        <p>{t("workflow.noSteps")}</p>
        <p className="text-xs mt-1">{t("workflow.stepsHint")}</p>
      </div>
    );
  }

  return (
    <div className="p-3">
      {workflowSteps.map((step) => {
        const isExpanded = expandedSteps[step.step_id];
        const isRunning = step.status === "running";
        const isCompleted = step.status === "completed";
        const isFailed = step.status === "failed";

        return (
          <div key={step.step_id} className="mb-2">
            {/* Step header */}
            <div
              onClick={() => toggleExpand(step.step_id)}
              className={`flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer text-sm transition-all duration-200 ease-out hover:bg-surface-50 ${
                isFailed ? "text-semantic-danger-700" : isRunning ? "text-brand-600" : "text-surface-700"
              }`}
            >
              {/* Status icon */}
              {isRunning ? (
                <svg className="w-4 h-4 shrink-0 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : isCompleted ? (
                <svg className="w-4 h-4 shrink-0 text-semantic-success-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : isFailed ? (
                <svg className="w-4 h-4 shrink-0 text-semantic-danger-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4 shrink-0 text-surface-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}

              {/* Step type badge */}
              <span className={`badge shrink-0 ${
                step.step_type === "tool_call" ? "bg-semantic-purple-50 text-semantic-purple-700" :
                step.step_type === "llm_call" ? "bg-semantic-info-50 text-semantic-info-700" :
                "bg-surface-100 text-surface-600"
              }`}>
                {step.step_type}
              </span>

              {/* Step name */}
              <span className="truncate">{step.step_name}</span>

              {/* Expand chevron */}
              {(step.output || step.error) && (
                <svg
                  className={`w-3.5 h-3.5 shrink-0 ml-auto transition-transform duration-200 text-surface-400 ${isExpanded ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              )}
            </div>

            {/* Expanded output */}
            {isExpanded && (step.output || step.error) && (
              <div className="ml-6 border-l border-surface-200/60 pl-3 py-1">
                {step.error ? (
                  <pre className="text-xs text-semantic-danger-700 whitespace-pre-wrap break-all bg-semantic-danger-50 p-3 rounded-xl">
                    {step.error}
                  </pre>
                ) : (
                  <pre className="text-xs text-surface-600 whitespace-pre-wrap break-all bg-surface-50 p-3 rounded-xl max-h-32 overflow-y-auto font-mono">
                    {step.output}
                  </pre>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
