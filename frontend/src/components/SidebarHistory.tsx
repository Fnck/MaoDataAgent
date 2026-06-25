import { useStore } from "../store";
import { useTranslation } from "react-i18next";

export default function SidebarHistory() {
  const { t } = useTranslation();
  const conversations = useStore((s) => s.conversations);
  const currentConversationId = useStore((s) => s.currentConversationId);
  const selectConversation = useStore((s) => s.selectConversation);
  const createConversation = useStore((s) => s.createConversation);
  const deleteConversation = useStore((s) => s.deleteConversation);

  const handleNew = async () => {
    const id = await createConversation();
    await selectConversation(id);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <button
          onClick={handleNew}
          className="btn-primary w-full py-2.5 text-sm"
        >
          {t("sidebar.newChat")}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center mx-2 px-3 py-2.5 cursor-pointer rounded-xl transition-all duration-200 ease-out ${
              conv.id === currentConversationId
                ? "bg-brand-50 text-brand-700"
                : "hover:bg-surface-50 text-surface-700"
            }`}
            onClick={() => selectConversation(conv.id)}
          >
            <span className="flex-1 text-sm truncate">
              {conv.title || t("sidebar.newChat")}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(t("sidebar.deleteConversation"))) {
                  deleteConversation(conv.id);
                }
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-surface-200 text-surface-400 hover:text-semantic-danger-500 transition-all duration-200 ease-out"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}

        {conversations.length === 0 && (
          <div className="p-6 text-center text-surface-400 text-sm">
            {t("sidebar.noConversations")}
          </div>
        )}
      </div>
    </div>
  );
}
