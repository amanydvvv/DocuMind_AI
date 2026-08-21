import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

/* ── SVG Outline Icons (consistent stroke weight) ── */
const IconLayers = ({ color }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
  </svg>
);
const IconChecklist = ({ color }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
  </svg>
);
const IconShield = ({ color }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);
const IconNetwork = ({ color }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="5" r="3" /><circle cx="5" cy="19" r="3" /><circle cx="19" cy="19" r="3" />
    <path d="M12 8v4M5.5 16.5L10 12M18.5 16.5L14 12" />
  </svg>
);

const SUGGESTION_CARDS = [
  {
    Icon: IconLayers,
    color: '#00d68f',
    bg: 'rgba(0,214,143,0.07)',
    border: 'rgba(0,214,143,0.18)',
    title: 'Architectural Synthesis',
    prompt: 'Summarize the key architectural decisions and system design tradeoffs in the uploaded documents.',
  },
  {
    Icon: IconChecklist,
    color: '#818cf8',
    bg: 'rgba(129,140,248,0.07)',
    border: 'rgba(129,140,248,0.18)',
    title: 'Requirement Extraction',
    prompt: 'Extract all functional constraints, performance metrics, and deadlines mentioned in the corpus.',
  },
  {
    Icon: IconShield,
    color: '#94a3b8',
    bg: 'rgba(148,163,184,0.06)',
    border: 'rgba(148,163,184,0.15)',
    title: 'Security & Compliance',
    prompt: 'Review the documents for any compliance protocols, security guidelines, or regulatory obligations.',
  },
  {
    Icon: IconNetwork,
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
      <div className="flex flex-col items-center justify-center h-full px-4 pb-4">
        {/* Hero — tighter spacing */}
        <div className="relative mb-5">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center animate-float-micro"
            style={{
              background: 'linear-gradient(135deg, #091410 0%, #0d2018 100%)',
              border: '1px solid rgba(0,214,143,0.25)',
              boxShadow: '0 0 40px rgba(0,214,143,0.15), 0 0 80px rgba(0,214,143,0.06)',
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00d68f" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div
            className="absolute -inset-3 rounded-3xl pointer-events-none animate-pulse"
            style={{ background: 'radial-gradient(circle, rgba(0,214,143,0.08) 0%, transparent 70%)' }}
          />
        </div>

        <h2 className="text-2xl font-bold text-text mb-2 tracking-tight text-center">
          What would you like to uncover?
        </h2>
        {/* Fix 7: bumped subtext color to #A0AAB0 for WCAG AA contrast */}
        <p className="text-sm text-center max-w-sm mb-5 leading-relaxed" style={{ color: '#A0AAB0' }}>
          KueryCore uses{' '}
          <span className="font-semibold" style={{ color: '#00d68f' }}>Hybrid Search</span>
          {' '}(Vector + BM25) and{' '}
          <span className="font-semibold" style={{ color: '#00ffaa' }}>Vision OCR</span>
          {' '}to deliver grounded answers with strict citation fidelity.
        </p>

        {/* Suggestion Cards — tighter gap */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-2xl">
          {SUGGESTION_CARDS.map((card) => (
            <button
              key={card.title}
              onClick={() => onSendMessage?.(card.prompt)}
              className="group text-left p-3.5 rounded-xl transition-all duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-[#00d68f] focus-visible:outline-none"
              style={{
                background: card.bg,
                border: `1px solid ${card.border}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = `0 8px 24px ${card.bg.replace('0.07', '0.25').replace('0.06', '0.2')}`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <card.Icon color={card.color} />
                <span className="text-xs font-semibold" style={{ color: card.color }}>{card.title}</span>
                <span
                  className="ml-auto text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: card.color }}
                >→</span>
              </div>
              <p className="text-[11px] leading-relaxed line-clamp-2" style={{ color: '#8a9a90' }}>{card.prompt}</p>
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
            className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
            style={{
              background: 'linear-gradient(135deg, #091410, #0d2018)',
              border: '1px solid rgba(0,214,143,0.3)',
              boxShadow: '0 0 12px rgba(0,214,143,0.15)',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00d68f" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
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