import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-200`}>
      <div
        className="max-w-[85%] md:max-w-[78%] rounded-2xl px-5 py-4"
        style={
          isUser
            ? {
                background: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%)',
                color: '#09090b',
                fontWeight: 500,
                borderRadius: '18px 18px 4px 18px',
                boxShadow: '0 4px 20px rgba(245,158,11,0.3), 0 1px 0 rgba(255,255,255,0.2) inset',
              }
            : {
                background: 'rgba(24,27,35,0.8)',
                border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: '18px 18px 18px 4px',
                boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                backdropFilter: 'blur(8px)',
              }
        }
      >
        <div className={`markdown text-[13.5px] leading-relaxed ${isUser ? 'text-slate-900' : ''}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div
            className="mt-4 pt-3"
            style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center gap-1.5 mb-2.5">
              <span style={{ color: '#f59e0b', fontSize: '11px' }}>◈</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>
                Grounding Sources ({message.citations.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((cit, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick && onCitationClick(cit)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer"
                  style={{
                    background: 'rgba(245,158,11,0.07)',
                    border: '1px solid rgba(245,158,11,0.18)',
                    color: '#cbd5e1',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(245,158,11,0.14)';
                    e.currentTarget.style.borderColor = 'rgba(245,158,11,0.35)';
                    e.currentTarget.style.color = '#fde68a';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(245,158,11,0.07)';
                    e.currentTarget.style.borderColor = 'rgba(245,158,11,0.18)';
                    e.currentTarget.style.color = '#cbd5e1';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                  title={
                    cit.source === 'ocr'
                      ? 'Extracted via Vision OCR'
                      : `Relevance: ${((cit.score || 0) * 100).toFixed(1)}%`
                  }
                >
                  <span style={{ color: '#f59e0b', fontSize: '10px' }}>⬡</span>
                  <span className="truncate max-w-[130px]">
                    {cit.filename || cit.metadata?.filename || 'Document'}
                  </span>
                  {(cit.page_number || cit.metadata?.page_number) && (
                    <span
                      className="px-1.5 py-0.5 text-[9px] font-bold rounded"
                      style={{ background: 'rgba(245,158,11,0.2)', color: '#fde68a' }}
                    >
                      p.{cit.page_number || cit.metadata?.page_number}
                    </span>
                  )}
                  {cit.source === 'ocr' && (
                    <span
                      className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded flex items-center gap-0.5"
                      style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.25)' }}
                    >
                      <span>◬</span>
                      <span>OCR</span>
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}