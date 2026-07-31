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
          ? 'bg-blue-50 border-blue-200 text-blue-900 font-medium shadow-sm'
          : 'bg-white border-transparent hover:bg-gray-100 text-text'
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
        className="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-red-500 rounded transition-opacity"
        title="Delete conversation"
      >
        🗑️
      </button>
    </div>
  );
}
