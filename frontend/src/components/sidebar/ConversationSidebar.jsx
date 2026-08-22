import { useState } from 'react';
import ConversationItem from './ConversationItem';

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
  isLoading = false,
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = (conversations || []).filter(conv => 
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top New Chat Action */}
      <div className="p-3.5 border-b border-border bg-surface/50 backdrop-blur-sm">
        <button
          onClick={onStartNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 clay-btn rounded-xl text-xs tracking-tight cursor-pointer"
        >
          <span className="text-[11px]">◇</span>
          <span>New Research Thread</span>
        </button>
      </div>

      {/* Search Input — Glassmorphic & Crisp */}
      <div className="px-3 py-2.5 border-b border-border-subtle">
        <input
          type="text"
          placeholder="Search threads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 text-xs text-white bg-surface-muted/70 backdrop-blur-md border border-white/[0.08] focus:border-emerald-400/80 rounded-xl focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-400/40 transition-all placeholder:text-slate-400 shadow-inner"
        />
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="flex items-center justify-between px-2 py-1.5 mb-1">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <span className="text-primary text-[10px]">⬡</span>
            <span>Conversations</span>
          </span>
          <span className="text-[10px] font-bold text-emerald-300 px-2 py-0.5 rounded-full bg-primary-soft border border-primary-border">
            {isLoading ? '…' : filteredConversations.length}
          </span>
        </div>

        {isLoading ? (
          <div className="space-y-1.5 py-1">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-white/[0.04] bg-surface/30"
              >
                <div className="w-2.5 h-2.5 rounded-full skeleton-shimmer flex-shrink-0" />
                <div className="flex-1 flex flex-col gap-1.5 min-w-0">
                  <div className="h-3 skeleton-shimmer rounded-md" style={{ width: `${55 + (n * 10)}%` }} />
                  <div className="h-2 skeleton-shimmer rounded-md w-12" />
                </div>
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 px-4 border border-dashed border-border rounded-xl mt-2">
            <p className="text-xs text-text-muted font-normal">
              No threads yet. Start a new chat to query documents.
            </p>
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-center py-8 px-4 border border-dashed border-border rounded-xl mt-2">
            <p className="text-xs text-text-muted font-normal">
              No conversations found.
            </p>
          </div>
        ) : (
          filteredConversations.map((conv) => (
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