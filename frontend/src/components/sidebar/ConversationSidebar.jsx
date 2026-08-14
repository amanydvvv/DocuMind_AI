import ConversationItem from './ConversationItem';
import Icon from '../shared/Icon';

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
}) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top New Chat Action */}
      <div className="p-3.5 border-b border-border bg-surface/40">
        <button
          onClick={onStartNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-primary text-white font-medium rounded-xl hover:bg-primary-hover shadow-[0_2px_12px_rgba(79,70,229,0.3),inset_0_1px_0_0_rgba(255,255,255,0.2)] active:scale-[0.98] transition-all duration-150 text-xs tracking-tight cursor-pointer"
        >
          <Icon name="plus" size={14} />
          <span>New Research Thread</span>
        </button>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="flex items-center justify-between px-2 py-1.5 mb-1">
          <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
            Conversations
          </span>
          <span className="text-[10px] font-medium text-text-muted px-1.5 py-0.5 rounded-full bg-surface-muted border border-border-subtle">
            {conversations.length}
          </span>
        </div>

        {conversations.length === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-xs text-text-muted font-normal">
              No threads yet. Start a new chat to query documents.
            </p>
          </div>
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