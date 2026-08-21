import Icon from '../shared/Icon';

export default function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}) {
  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMin = Math.floor((now - date) / (1000 * 60));
    
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const isSameYear = date.getFullYear() === now.getFullYear();
    return date.toLocaleDateString(undefined, { 
      month: 'short', 
      day: 'numeric',
      ...(isSameYear ? {} : { year: 'numeric' })
    });
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation thread?')) {
      onDelete(conversation.id);
    }
  };

  return (
    <div
      onClick={() => onSelect(conversation.id)}
      className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 border ${
        isActive
          ? 'bg-primary-soft border-primary-border text-text font-medium shadow-[0_4px_12px_rgba(0,0,0,0.4)]'
          : 'bg-transparent border-transparent hover:bg-surface-muted/60 text-text-secondary hover:text-text'
      }`}
    >
      {/* Active Left Indicator Bar */}
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 rounded-r-full bg-primary" style={{ boxShadow: '0 0 8px var(--color-border-glow)' }}></div>
      )}

      <div className="flex-1 min-w-0 pr-2 pl-1.5 flex items-center gap-2">
        <span className={`text-[10px] flex-shrink-0 ${isActive ? 'text-primary' : 'text-text-muted group-hover:text-text-secondary'}`}>
          {isActive ? '◆' : '◇'}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs truncate font-medium">
            {conversation.title || 'New Chat'}
          </p>
          <p
            className="text-[10px] text-text-muted mt-0.5 font-normal"
            title={conversation.updated_at || conversation.created_at ? new Date(conversation.updated_at || conversation.created_at).toLocaleString() : ''}
          >
            {formatTime(conversation.updated_at || conversation.created_at)}
          </p>
        </div>
      </div>

      <button
        onClick={handleDelete}
        className="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-danger-text hover:bg-danger-soft rounded-md transition-all duration-150 cursor-pointer"
        aria-label={`Delete conversation: ${conversation.title || 'New Chat'}`}
        title="Delete conversation"
      >
        <Icon name="trash" size={13} />
      </button>
    </div>
  );
}