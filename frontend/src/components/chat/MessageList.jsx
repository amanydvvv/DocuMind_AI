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
      <div className="flex flex-col gap-6 max-w-3xl mx-auto w-full px-4 py-6 animate-in fade-in duration-200">
        {/* User Bubble Skeleton */}
        <div className="flex justify-end w-full">
          <div
            className="w-64 h-12 rounded-2xl rounded-tr-xs skeleton-shimmer"
            style={{
              border: '1px solid rgba(0, 214, 143, 0.15)',
              background: 'rgba(0, 214, 143, 0.08)',
            }}
          />
        </div>

        {/* Assistant Bubble Skeleton */}
        <div className="flex justify-start w-full">
          <div
            className="w-full max-w-2xl rounded-2xl rounded-tl-xs p-5 flex flex-col gap-3"
            style={{
              background: 'linear-gradient(145deg, rgba(13, 29, 21, 0.8) 0%, rgba(9, 20, 16, 0.9) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(16px)',
            }}
          >
            <div className="h-3.5 skeleton-shimmer rounded-md w-full" />
            <div className="h-3.5 skeleton-shimmer rounded-md w-11/12" />
            <div className="h-3.5 skeleton-shimmer rounded-md w-4/5" />
            <div className="h-3.5 skeleton-shimmer rounded-md w-2/3" />

            {/* Citations Skeleton */}
            <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center gap-2">
              <div className="w-20 h-6 skeleton-shimmer rounded-lg" />
              <div className="w-24 h-6 skeleton-shimmer rounded-lg" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 pb-4">
        <h2 className="text-2xl font-bold text-text mb-6 tracking-tight text-center">
          What would you like to uncover?
        </h2>

        {/* Suggestion Cards — Glassmorphic & High Contrast */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
          {SUGGESTION_CARDS.map((card) => (
            <button
              key={card.title}
              onClick={() => onSendMessage?.(card.prompt)}
              className="group text-left p-4 rounded-2xl transition-all duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-[#00d68f] focus-visible:outline-none"
              style={{
                background: 'linear-gradient(180deg, #1e2621 0%, #0d1511 100%)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.09)',
                boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 4px 20px rgba(0, 0, 0, 0.4)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.borderColor = card.color;
                e.currentTarget.style.boxShadow = `0 10px 30px rgba(0,0,0,0.5), 0 0 20px ${card.color}25, inset 0 1px 0 rgba(255,255,255,0.25)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.09)';
                e.currentTarget.style.boxShadow = 'inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 4px 20px rgba(0, 0, 0, 0.4)';
              }}
            >
              <div className="flex items-center gap-2.5 mb-2">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{
                    background: `${card.color}15`,
                    border: `1px solid ${card.color}35`,
                  }}
                >
                  <card.Icon color={card.color} />
                </div>
                <span className="text-xs font-bold text-white tracking-tight">{card.title}</span>
                <span
                  className="ml-auto text-xs opacity-0 group-hover:opacity-100 transition-opacity font-bold"
                  style={{ color: card.color }}
                >→</span>
              </div>
              <p className="text-xs leading-relaxed text-slate-300 font-normal line-clamp-2">{card.prompt}</p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto w-full">
      {messages.map((msg, index) => (
        <MessageBubble
          key={msg.id || `msg-${index}-${msg.role}`}
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