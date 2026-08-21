import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

const SUGGESTION_CARDS = [
  {
    icon: '◈',
    color: '#00d68f',
    bg: 'rgba(0,214,143,0.07)',
    border: 'rgba(0,214,143,0.18)',
    title: 'Architectural Synthesis',
    prompt: 'Summarize the key architectural decisions and system design tradeoffs in the uploaded documents.',
  },
  {
    icon: '▣',
    color: '#818cf8',
    bg: 'rgba(129,140,248,0.07)',
    border: 'rgba(129,140,248,0.18)',
    title: 'Requirement Extraction',
    prompt: 'Extract all functional constraints, performance metrics, and deadlines mentioned in the corpus.',
  },
  {
    icon: '◬',
    color: '#f87171',
    bg: 'rgba(248,113,113,0.07)',
    border: 'rgba(248,113,113,0.18)',
    title: 'Security & Compliance',
    prompt: 'Review the documents for any compliance protocols, security guidelines, or regulatory obligations.',
  },
  {
    icon: '◆',
    color: '#34d399',
    bg: 'rgba(52,211,153,0.07)',
    border: 'rgba(52,211,153,0.18)',
    title: 'Entity Cross-Reference',
    prompt: 'Identify key stakeholders, project roles, and referenced systems across all documents.',
  },
];

export default function MessageList({
  messages,
  isLoadingHistory,
  isGenerating,
  onCitationClick,
  onSendMessage,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  if (isLoadingHistory) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
            style={{ borderColor: '#00d68f', borderTopColor: 'transparent' }}
          />
          <p className="text-xs text-text-muted">Loading history…</p>
        </div>
      </div>
    );
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 pb-8">
        {/* Hero Icon */}
        <div className="relative mb-8">
          <div
            className="w-20 h-20 rounded-2xl flex items-center justify-center text-3xl font-black animate-float-micro"
            style={{
              background: 'linear-gradient(135deg, #091410 0%, #0d2018 100%)',
              border: '1px solid rgba(0,214,143,0.25)',
              boxShadow: '0 0 40px rgba(0,214,143,0.15), 0 0 80px rgba(0,214,143,0.06)',
              color: '#00d68f',
            }}
          >
            ◈
          </div>
          {/* Outer glow rings */}
          <div
            className="absolute -inset-3 rounded-3xl pointer-events-none animate-pulse"
            style={{ background: 'radial-gradient(circle, rgba(0,214,143,0.08) 0%, transparent 70%)' }}
          />
        </div>

        <h2 className="text-2xl font-bold text-text mb-3 tracking-tight text-center">
          What would you like to uncover?
        </h2>
        <p className="text-sm text-text-muted text-center max-w-sm mb-8 leading-relaxed">
          KueryCore uses{' '}
          <span className="font-semibold" style={{ color: '#00d68f' }}>Hybrid Search</span>
          {' '}(Vector + BM25) and{' '}
          <span className="font-semibold" style={{ color: '#00ffaa' }}>Vision OCR</span>
          {' '}to deliver grounded answers with strict citation fidelity.
        </p>

        {/* Suggestion Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
          {SUGGESTION_CARDS.map((card) => (
            <button
              key={card.title}
              onClick={() => onSendMessage?.(card.prompt)}
              className="group text-left p-4 rounded-xl transition-all duration-200 cursor-pointer"
              style={{
                background: card.bg,
                border: `1px solid ${card.border}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = `0 8px 24px ${card.bg.replace('0.07', '0.3')}`;
                e.currentTarget.style.borderColor = card.color.replace(')', ',0.4)').replace('rgb', 'rgba');
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = card.border;
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-base" style={{ color: card.color }}>{card.icon}</span>
                <span className="text-xs font-semibold" style={{ color: card.color }}>{card.title}</span>
                <span
                  className="ml-auto text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: card.color }}
                >→</span>
              </div>
              <p className="text-[11px] text-text-muted leading-relaxed line-clamp-2">{card.prompt}</p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto w-full">
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          onCitationClick={onCitationClick}
        />
      ))}
      {isGenerating && (
        <div className="flex items-start gap-3">
          <div
            className="w-7 h-7 rounded-xl flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
            style={{
              background: 'linear-gradient(135deg, #091410, #0d2018)',
              border: '1px solid rgba(0,214,143,0.3)',
              boxShadow: '0 0 12px rgba(0,214,143,0.15)',
              color: '#00d68f',
            }}
          >
            ◈
          </div>
          <div
            className="px-4 py-3 rounded-2xl text-sm"
            style={{
              background: 'rgba(9,20,16,0.8)',
              border: '1px solid rgba(0,214,143,0.12)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <div className="flex items-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full"
                  style={{
                    background: '#00d68f',
                    boxShadow: '0 0 6px rgba(0,214,143,0.7)',
                    animation: `bounce 0.9s ease-in-out ${i * 0.18}s infinite`,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}