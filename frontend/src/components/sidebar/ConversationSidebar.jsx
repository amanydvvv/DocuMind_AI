import { useState } from 'react';
import ConversationItem from './ConversationItem';
import Icon from '../shared/Icon';

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter(conv => 
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top New Chat Action */}
      <div className="p-3.5 border-b border-border bg-surface">
        <button
          onClick={onStartNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 clay-btn rounded-xl text-xs tracking-tight cursor-pointer"
        >
          <span className="text-[11px]">◇</span>
          <span>New Research Thread</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="px-3 py-2 border-b border-border-subtle">
        <input
          type="text"
          placeholder="Search threads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-1.5 text-xs text-text bg-surface-muted/50 backdrop-blur-md border border-border rounded-lg focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary transition-all placeholder:text-text-muted"
        />
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="flex items-center justify-between px-2 py-1.5 mb-1">
          <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
            <span className="text-primary text-[10px]">⬡</span>
            <span>Conversations</span>
          </span>
          <span className="text-[10px] font-semibold text-primary-light px-1.5 py-0.5 rounded-full bg-primary-soft border border-primary-border">
            {filteredConversations.length}
          </span>
        </div>

        {conversations.length === 0 ? (
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