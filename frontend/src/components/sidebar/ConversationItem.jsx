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
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation?')) {
      onDelete(conversation.id);
    }
  };

  return (
    <div
      onClick={() => onSelect(conversation.id)}
      className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border ${
        isActive
          ? 'bg-primary-soft border-primary-border text-primary-light font-medium shadow-sm'
          : 'bg-surface border-transparent hover:bg-surface-muted text-text'
      }`}
    >
      <div className="flex-1 min-w-0 pr-2">
        <p className="text-sm truncate">
          {conversation.title || 'New Chat'}
        </p>
        <p className="text-xs text-text-muted mt-0.5">
          {formatTime(conversation.updated_at || conversation.created_at)}
        </p>
      </div>

      <button
        onClick={handleDelete}
        className="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-danger rounded transition-opacity"
        aria-label={`Delete conversation: ${conversation.title || 'New Chat'}`}
        title="Delete conversation"
      >
        <Icon name="trash" size={15} />
      </button>
    </div>
  );
}