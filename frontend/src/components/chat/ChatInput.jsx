import { useState, useRef, useEffect } from 'react';
import Icon from '../shared/Icon';

export default function ChatInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea smoothly
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [message]);

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative rounded-2xl bg-surface border border-border p-2.5 transition-all duration-200 focus-within:border-primary-border focus-within:shadow-[0_8px_32px_rgba(245,158,11,0.18)] flex flex-col gap-2 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_12px_28px_rgba(0,0,0,0.5)]">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents (or start general inquiry)..."
          className="w-full bg-transparent px-3 py-2 text-[13.5px] text-text placeholder:text-text-muted focus:outline-none resize-none min-h-[44px] max-h-40 leading-relaxed font-normal"
          rows={1}
          disabled={disabled}
        />
        
        <div className="flex items-center justify-between px-2 pt-1.5 border-t border-border-subtle">
          <span className="text-[11px] text-text-muted select-none flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 rounded bg-surface-muted border border-border text-[10px] text-text-secondary font-mono">↵</kbd>
            <span>to send</span>
            <span className="text-text-muted/60 ml-1">•</span>
            <kbd className="px-1.5 py-0.5 rounded bg-surface-muted border border-border text-[10px] text-text-secondary font-mono ml-1">Shift+↵</kbd>
            <span>new line</span>
          </span>

          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className="h-8 px-4 clay-btn rounded-xl text-xs font-bold disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5 cursor-pointer"
          >
            <span>Dispatch</span>
            <span className="text-[10px] font-bold">→</span>
          </button>
        </div>
      </div>
    </form>
  );
}