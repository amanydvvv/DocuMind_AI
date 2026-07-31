import ConversationItem from './ConversationItem';

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
}) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top New Chat Button */}
      <div className="p-3 border-b border-border bg-white">
        <button
          onClick={onStartNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-primary text-white font-medium rounded-xl hover:bg-primary-hover shadow-sm transition-colors text-sm"
        >
          <span>💬</span>
          <span>+ New Chat</span>
        </button>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider px-2 mb-2">
          Chat History ({conversations.length})
        </p>

        {conversations.length === 0 ? (
          <p className="text-xs text-text-muted px-2 py-3 italic">
            No previous conversations.
          </p>
        ) : (
          conversations.map((conv) => (
            <ConversationItem
              key={conv.id}
              conversation={conv}
              isActive={conv.id === activeConversationId}
              onSelect={onSelectConversation}
              onDelete={onDeleteConversation}
            />
          ))
        )}
      </div>
    </div>
  );
}
