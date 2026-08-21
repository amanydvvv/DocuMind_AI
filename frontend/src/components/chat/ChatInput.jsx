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

          {/* Dispatch button */}
          <button
            type="submit"
            aria-label="Send message"
            disabled={!canSend}
            className="h-8 px-4 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-all duration-150 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
            style={
              canSend
                ? {
                    background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                    color: '#030a06',
                    boxShadow: '0 2px 12px rgba(0,214,143,0.4), inset 0 1px 0 rgba(255,255,255,0.3)',
                  }
                : {
                    background: 'rgba(255,255,255,0.05)',
                    color: 'rgba(255,255,255,0.2)',
                    cursor: 'not-allowed',
                  }
            }
            onMouseEnter={(e) => {
              if (canSend) {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,214,143,0.5), inset 0 1px 0 rgba(255,255,255,0.35)';
              }
            }}
            onMouseLeave={(e) => {
              if (canSend) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,214,143,0.4), inset 0 1px 0 rgba(255,255,255,0.3)';
              }
            }}
            onMouseDown={(e) => {
              if (canSend) e.currentTarget.style.transform = 'scale(0.97)';
            }}
            onMouseUp={(e) => {
              if (canSend) e.currentTarget.style.transform = 'translateY(-1px)';
            }}
          >
            <span>Ask</span>
            <span className="text-[10px] font-black">→</span>
          </button>
        </div>
      </div>
    </form>
  );
}