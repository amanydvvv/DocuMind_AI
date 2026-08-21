import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import BrandIcon from '../shared/BrandIcon';

export default function MessageList({
  messages,
  isLoadingHistory,
  isGenerating,
  onCitationClick,
  onSendMessage,
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  if (isLoadingHistory) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center gap-3">
        <div
          className="w-8 h-8 rounded-full border-2 border-amber-400 border-t-transparent animate-spin"
          style={{ boxShadow: '0 0 12px rgba(245,158,11,0.3)' }}
        />
        <p className="text-xs font-medium text-text-muted">Loading research history...</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4 max-w-2xl mx-auto select-none">

        {/* Hero icon with multi-layer glow */}
        <div className="relative mb-8">
          <div
            className="absolute inset-0 rounded-3xl blur-3xl animate-pulse"
            style={{ background: 'radial-gradient(circle, rgba(245,158,11,0.2) 0%, transparent 70%)', transform: 'scale(1.8)' }}
          />
          <div
            className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #1c1a0e 0%, #2a1f00 50%, #1c1a0e 100%)',
              border: '1px solid rgba(245,158,11,0.35)',
              boxShadow: '0 0 32px rgba(245,158,11,0.25), 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)',
            }}
          >
            <BrandIcon size={32} />
          </div>
        </div>

        <h2
          className="text-2xl font-bold mb-3 tracking-tight"
          style={{
            background: 'linear-gradient(135deg, #f1f5f9 0%, #fde68a 60%, #f1f5f9 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          What would you like to uncover?
        </h2>
        <p className="text-sm text-text-muted max-w-sm mb-10 leading-relaxed">
          KueryCore uses{' '}
          <span style={{ color: '#fde68a', fontWeight: 600 }}>Hybrid Search</span> (Vector + BM25) and{' '}
          <span style={{ color: '#fde68a', fontWeight: 600 }}>Vision OCR</span> to deliver grounded answers
          with strict citation fidelity.
        </p>

        {/* Suggestion Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full text-left">
          {[
            {
              glyph: '◈',
              color: '#f59e0b',
              title: 'Architectural Synthesis',
              prompt: 'Summarize the key architectural decisions and system design tradeoffs in the uploaded documents.',
            },
            {
              glyph: '▣',
              color: '#818cf8',
              title: 'Requirement Extraction',
              prompt: 'Extract all functional constraints, performance metrics, and deadlines mentioned in the corpus.',
            },
            {
              glyph: '◬',
              color: '#f43f5e',
              title: 'Security & Compliance',
              prompt: 'Review the documents for any compliance standards, encryption guidelines, or security policies.',
            },
            {
              glyph: '◆',
              color: '#34d399',
              title: 'Entity Cross-Reference',
              prompt: 'Identify key stakeholders, project roles, and referenced external services across all sections.',
            },
          ].map((suggestion) => (
            <button
              key={suggestion.title}
              type="button"
              onClick={() => onSendMessage && onSendMessage(suggestion.prompt)}
              className="group p-4 rounded-xl text-left transition-all duration-200 cursor-pointer relative overflow-hidden"
              style={{
                background: 'rgba(255,255,255,0.025)',
                border: '1px solid rgba(255,255,255,0.07)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                e.currentTarget.style.borderColor = `${suggestion.color}44`;
                e.currentTarget.style.boxShadow = `0 4px 24px rgba(0,0,0,0.3), 0 0 0 1px ${suggestion.color}22`;
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.025)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {/* Corner glow */}
              <div
                className="absolute top-0 right-0 w-16 h-16 rounded-full pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                style={{ background: `radial-gradient(circle, ${suggestion.color}18, transparent 70%)`, transform: 'translate(30%, -30%)' }}
              />
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ background: `${suggestion.color}18`, color: suggestion.color, border: `1px solid ${suggestion.color}30` }}
                  >
                    {suggestion.glyph}
                  </span>
                  <span className="text-xs font-semibold text-text group-hover:text-white transition-colors">
                    {suggestion.title}
                  </span>
                </div>
                <span
                  className="text-xs text-text-muted group-hover:translate-x-0.5 transition-transform duration-150 flex-shrink-0"
                  style={{ color: suggestion.color + '99' }}
                >→</span>
              </div>
              <p className="text-[11px] text-text-muted leading-relaxed line-clamp-2 pl-8">
                "{suggestion.prompt}"
              </p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-5 max-w-3xl mx-auto w-full pb-6">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          message={msg}
          onCitationClick={onCitationClick}
        />
      ))}

      {/* Generating indicator */}
      {isGenerating && (
        <div className="flex w-full justify-start animate-in fade-in duration-200">
          <div
            className="rounded-2xl px-4 py-3 flex items-center gap-3 text-xs"
            style={{
              background: 'rgba(245,158,11,0.06)',
              border: '1px solid rgba(245,158,11,0.15)',
              boxShadow: '0 0 20px rgba(245,158,11,0.08)',
            }}
          >
            {/* Animated amber orbs */}
            <div className="flex items-center gap-1">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="w-1.5 h-1.5 rounded-full animate-bounce"
                  style={{
                    background: '#f59e0b',
                    boxShadow: '0 0 6px rgba(245,158,11,0.6)',
                    animationDelay: `${delay}ms`,
                  }}
                />
              ))}
            </div>
            <span className="font-medium" style={{ color: '#fde68a' }}>
              Retrieving citations &amp; synthesizing output...
            </span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}