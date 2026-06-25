import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "../store";
import * as api from "../api";
import DebugCard from "./DebugCard";
import type { DebugEvent } from "../types";

export default function ChatArea() {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const messages = useStore((s) => s.messages);
  const currentConversationId = useStore((s) => s.currentConversationId);
  const selectedFiles = useStore((s) => s.selectedFiles);
  const selectedTables = useStore((s) => s.selectedTables);
  const isStreaming = useStore((s) => s.isStreaming);
  const setStreaming = useStore((s) => s.setStreaming);
  const addMessage = useStore((s) => s.addMessage);
  const appendToLastAssistant = useStore((s) => s.appendToLastAssistant);
  const createConversation = useStore((s) => s.createConversation);
  const setWorkflowStep = useStore((s) => s.setWorkflowStep);
  const updateWorkflowStep = useStore((s) => s.updateWorkflowStep);
  const clearWorkflowSteps = useStore((s) => s.clearWorkflowSteps);
  const debugEvents = useStore((s) => s.debugEvents);
  const addDebugEvent = useStore((s) => s.addDebugEvent);
  const assignDebugEventMessageId = useStore((s) => s.assignDebugEventMessageId);
  const openDebugDrawer = useStore((s) => s.openDebugDrawer);
  const openOntologyPanel = useStore((s) => s.openOntologyPanel);

  const [input, setInput] = useState("");
  const [, setStreamTick] = useState(0);
  const streamContentRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [streamFinished, setStreamFinished] = useState(false);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, debugEvents]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    let convId = currentConversationId;
    if (!convId) {
      convId = await createConversation();
      // Set conversation ID directly without fetching (new conversation has no messages yet)
      useStore.setState({ currentConversationId: convId, messages: [], debugEvents: [] });
    }

    // Add user message to UI
    addMessage({
      id: Date.now(),
      role: "user",
      content: input,
      created_at: new Date().toISOString(),
    });

    const messageText = input;
    setInput("");
    setStreaming(true);
    streamContentRef.current = "";
    setStreamTick(0);
    clearWorkflowSteps();

    try {
      const chatRequest = {
        message: messageText,
        conversation_id: convId,
        context: {
          selected_files: selectedFiles,
          selected_tables: selectedTables,
        },
      };

      for await (const event of api.streamChat(token, chatRequest)) {
        if (event.type === "chunk") {
          streamContentRef.current += event.content;
          setStreamTick((n) => n + 1);
        } else if (event.type === "end") {
          // Add completed assistant message to Zustand with the real DB message_id
          addMessage({
            id: event.message_id,
            role: "assistant",
            content: streamContentRef.current,
            created_at: new Date().toISOString(),
          });
          assignDebugEventMessageId(event.message_id);
        } else if (event.type === "error") {
          appendToLastAssistant(`\n\n[Error: ${event.error}]`);
        } else if (event.type === "step_start") {
          setWorkflowStep({
            step_id: event.step_id,
            step_name: event.step_name,
            step_type: event.step_type,
            status: "running",
            output: null,
            error: null,
          });
        } else if (event.type === "step_end") {
          updateWorkflowStep(event.step_id, {
            status: "completed",
            output: event.output,
          });
        } else if (event.type === "step_error") {
          updateWorkflowStep(event.step_id, {
            status: "failed",
            error: event.error,
          });
        } else if (event.type === "debug") {
          const debugEvent: DebugEvent = {
            event_id: event.event_id,
            conversation_id: convId!,
            category: event.category,
            data: event.data,
            timestamp: event.timestamp,
            seq: String(event.seq ?? "0"),
            step_id: event.step_id ?? null,
            message_id: event.message_id ?? null,
          };
          addDebugEvent(debugEvent);
        }
      }
    } catch (err) {
      const errorMsg = `\n\n[Error: ${err instanceof Error ? err.message : t("chat.unknownError")}]`;
      streamContentRef.current += errorMsg;
      setStreamTick((n: number) => n + 1);
    } finally {
      setStreaming(false);
      setStreamFinished(true);
      setTimeout(() => setStreamFinished(false), 2000);
      // Refresh sidebar to pick up auto-generated conversation title
      useStore.getState().fetchConversations();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Parse seq string to numeric order
  const parseSeqOrder = (seq: string): number => parseInt(seq, 10) || 0;

  // Get debug events to display after a specific message
  const getDebugsForMessage = (msgId: number): DebugEvent[] => {
    return debugEvents
      .filter((d) => d.message_id === msgId)
      .sort((a, b) => parseSeqOrder(a.seq) - parseSeqOrder(b.seq));
  };

  // Get debug events without a message_id (pre-message assignment)
  const getUnassignedDebugs = (): DebugEvent[] => {
    return debugEvents
      .filter((d) => d.message_id === null)
      .sort((a, b) => parseSeqOrder(a.seq) - parseSeqOrder(b.seq));
  };

  if (!currentConversationId && messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-surface-400 animate-fade-in">
        <div className="text-center">
          <svg className="w-12 h-12 mx-auto mb-4 text-surface-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p className="text-lg mb-1 text-surface-500">{t("chat.startNew")}</p>
          <p className="text-sm">{t("chat.typeToBegin")}</p>
        </div>
      </div>
    );
  }

  // ── Computed once for rendering ────────────────────
  const unassignedDebugs = getUnassignedDebugs();

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl mx-auto space-y-5">
          {messages.map((msg, idx) => {
            if (msg.role === "user") {
              return (
                <div key={`${msg.id}-${idx}`} className="animate-slide-up">
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl px-5 py-3 text-sm bg-brand-500 text-white shadow-sm">
                      <div className="whitespace-pre-wrap break-words">
                        {msg.content || ""}
                      </div>
                    </div>
                  </div>
                </div>
              );
            }

            // Assistant message: debug process (if any) then the response
            const debugsForMsg =
              msg.id > 0 ? getDebugsForMessage(msg.id) : [];

            return (
              <div key={`${msg.id}-${idx}`}>
                {debugsForMsg.map((d) => (
                  <DebugCard key={`debug-${d.event_id}`} event={d} />
                ))}
                <div className="flex justify-start animate-slide-up">
                  <div className="max-w-[80%] rounded-2xl px-5 py-3 text-sm bg-white shadow-xs border border-surface-200/60 text-surface-800 prose prose-sm max-w-none">
                    {msg.content ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      <div className="whitespace-pre-wrap break-words">
                        {msg.content || ""}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Unassigned debug events (current round's process, shown during streaming) */}
          {unassignedDebugs.length > 0 && (
            <div className="space-y-0.5">
              {unassignedDebugs.map((d) => (
                <DebugCard key={`debug-${d.event_id}`} event={d} />
              ))}
            </div>
          )}

          {/* Streaming content */}
          {isStreaming && streamContentRef.current && (
            <div className="flex justify-start animate-slide-up">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 text-sm bg-white shadow-xs border border-surface-200/60 text-surface-800 prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {streamContentRef.current}
                </ReactMarkdown>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Streaming status bar */}
      <div className="px-6 shrink-0">
        <div className="max-w-3xl mx-auto h-7 flex items-center gap-2 text-xs">
          {isStreaming && (
            <div className="flex items-center gap-2 text-surface-500 transition-opacity">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
              </span>
              <span>Processing...</span>
            </div>
          )}
          {streamFinished && (
            <div className="flex items-center gap-1.5 text-emerald-600 transition-opacity">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span>Done</span>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-surface-200/60 bg-white/80 backdrop-blur-md px-6 py-4 shrink-0">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("chat.placeholder")}
            rows={1}
            className="input resize-none flex-1"
            disabled={isStreaming}
          />
          <button
            onClick={openDebugDrawer}
            className="p-2.5 rounded-xl text-surface-500 hover:bg-surface-100 active:scale-95 shrink-0 transition-all duration-200 ease-out"
            title={t("chat.debug")}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <button
            onClick={openOntologyPanel}
            className="p-2.5 rounded-xl text-surface-500 hover:bg-surface-100 active:scale-95 shrink-0 transition-all duration-200 ease-out"
            title={t("chat.ontologyConfig")}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="btn-primary shrink-0 px-4 py-2.5"
          >
            {isStreaming ? "..." : t("chat.send")}
          </button>
        </div>

        {/* Context indicator */}
        {(selectedFiles.length > 0 || selectedTables.length > 0) && (
          <div className="max-w-3xl mx-auto mt-2 flex gap-1.5 flex-wrap">
            {selectedFiles.map((f) => (
              <span
                key={f}
                className="badge bg-semantic-success-50 text-semantic-success-700"
              >
                {f.split("/").pop()}
              </span>
            ))}
            {selectedTables.map((t) => (
              <span
                key={t}
                className="badge bg-semantic-purple-50 text-semantic-purple-700"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
