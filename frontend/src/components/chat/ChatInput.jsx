import { useState, useRef, useEffect } from 'react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState('');
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [message]);

  const canSend = message.trim() && !disabled;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div
        className="relative rounded-2xl p-3 flex flex-col gap-2 transition-all duration-200"
        style={{
          background: 'linear-gradient(180deg, rgba(13, 29, 21, 0.88) 0%, rgba(9, 20, 16, 0.94) 100%)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: focused
            ? '1px solid rgba(0, 214, 143, 0.45)'
            : '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: focused
            ? '0 0 0 3px rgba(0, 214, 143, 0.18), 0 12px 40px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12)'
            : '0 8px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        }}
      >
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask anything about your documents (or start general inquiry)..."
          className="w-full bg-transparent px-3 py-2 text-[14px] text-white placeholder:text-slate-400 focus:outline-none resize-none min-h-[44px] max-h-40 leading-relaxed font-normal"
          rows={1}
          disabled={disabled}
        />

        <div
          className="flex items-center justify-between px-2 pt-2"
          style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
        >
          {/* Keyboard hints */}
          <span className="text-[11px] text-slate-400 flex items-center gap-1.5 select-none">
            <kbd className="px-1.5 py-0.5 rounded-md bg-white/[0.08] border border-white/[0.12] text-[10px] text-slate-200 font-mono font-semibold shadow-xs">↵</kbd>
            <span className="font-medium text-slate-300">send</span>
            <span className="text-white/20 mx-0.5">•</span>
            <kbd className="px-1.5 py-0.5 rounded-md bg-white/[0.08] border border-white/[0.12] text-[10px] text-slate-200 font-mono font-semibold shadow-xs">Shift+↵</kbd>
            <span className="font-medium text-slate-300">new line</span>
          </span>

          {/* Circular Dispatch button matching reference aesthetic */}
          <button
            type="submit"
            aria-label="Send message"
            disabled={!canSend}
            className="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer transition-all duration-150 focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:outline-none disabled:opacity-30 disabled:cursor-not-allowed"
            style={
              canSend
                ? {
                    background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                    color: '#020804',
                    boxShadow: '0 2px 10px rgba(0, 214, 143, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)',
                  }
                : {
                    background: 'rgba(255, 255, 255, 0.06)',
                    color: 'rgba(255, 255, 255, 0.3)',
                  }
            }
            onMouseEnter={(e) => {
              if (canSend) {
                e.currentTarget.style.transform = 'scale(1.06)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 214, 143, 0.7)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              if (canSend) {
                e.currentTarget.style.boxShadow = '0 2px 10px rgba(0, 214, 143, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)';
              }
            }}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </div>
      </div>
    </form>
  );
}