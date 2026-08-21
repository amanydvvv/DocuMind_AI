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
                background: 'linear-gradient(135deg, #00a86b 0%, #00d68f 50%, #00ffaa 100%)',
                color: '#020804',
                fontWeight: 600,
                borderRadius: '18px 18px 4px 18px',
                boxShadow: '0 4px 20px rgba(0,214,143,0.35), inset 0 1px 0 rgba(255,255,255,0.3)',
              }
            : {
                background: 'linear-gradient(145deg, rgba(13, 29, 21, 0.82) 0%, rgba(9, 20, 16, 0.9) 100%)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '18px 18px 18px 4px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
              }
        }
      >
        <div className={`markdown text-[14px] leading-relaxed ${isUser ? 'text-slate-950 font-medium' : 'text-slate-100'}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div
            className="mt-4 pt-3"
            style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
          >
            <div className="flex items-center gap-1.5 mb-2.5">
              <span style={{ color: '#00d68f', fontSize: '11px' }}>◈</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-300">
                Grounding Sources ({message.citations.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.citations.map((cit, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick && onCitationClick(cit)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl transition-all duration-150 cursor-pointer text-slate-100"
                  style={{
                    background: 'linear-gradient(135deg, rgba(0, 214, 143, 0.12) 0%, rgba(0, 214, 143, 0.05) 100%)',
                    border: '1px solid rgba(0, 214, 143, 0.28)',
                    backdropFilter: 'blur(8px)',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0,214,143,0.2)';
                    e.currentTarget.style.borderColor = 'rgba(0,214,143,0.5)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 4px 14px rgba(0, 214, 143, 0.3)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(0, 214, 143, 0.12) 0%, rgba(0, 214, 143, 0.05) 100%)';
                    e.currentTarget.style.borderColor = 'rgba(0, 214, 143, 0.28)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
                  }}
                  title={
                    cit.source === 'ocr'
                      ? 'Extracted via Vision OCR'
                      : `Relevance: ${((cit.score || 0) * 100).toFixed(1)}%`
                  }
                >
                  <span style={{ color: '#00d68f', fontSize: '10px' }}>⬡</span>
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