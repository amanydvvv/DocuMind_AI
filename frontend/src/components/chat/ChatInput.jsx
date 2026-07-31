import { useState } from 'react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-border bg-background">
      <div className="relative max-w-4xl mx-auto flex items-end gap-2">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents..."
          className="flex-1 max-h-32 min-h-[50px] p-3 rounded-xl border border-border bg-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none transition-all shadow-sm"
          rows={1}
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="h-[50px] px-6 bg-primary text-white font-medium rounded-xl hover:bg-primary-hover disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center justify-center"
        >
          Send
        </button>
      </div>
    </form>
  );
}
