import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Icon from '../shared/Icon';

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-200`}>
      <div 
        className={`max-w-[85%] md:max-w-[80%] rounded-2xl px-5 py-4 ${
          isUser 
            ? 'bg-primary text-white rounded-br-xs shadow-[0_4px_16px_rgba(79,70,229,0.25),inset_0_1px_0_0_rgba(255,255,255,0.2)]' 
            : 'glass-card text-text rounded-bl-xs'
        }`}
      >
        <div className="markdown text-[13.5px] leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
        
        {/* Render Citations if they exist and it's an AI message */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border-subtle">
            <div className="flex items-center gap-1.5 mb-2">
              <Icon name="target" size={12} className="text-primary-light" />
              <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Grounding Sources ({message.citations.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((cit, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick && onCitationClick(cit)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-surface-muted/80 text-text-secondary hover:text-text hover:bg-surface-elevated hover:border-primary-border rounded-lg transition-all duration-150 border border-border-subtle tactile-btn cursor-pointer shadow-xs"
                  title={cit.source === 'ocr' ? 'Extracted via Vision OCR from document scan' : `Relevance Score: ${((cit.score || 0) * 100).toFixed(1)}%`}
                >
                  <Icon name="docs" size={12} className="text-primary-light" />
                  <span className="truncate max-w-[140px]">
                    {cit.filename || cit.metadata?.filename || 'Document'}
                  </span>
                  {(cit.page_number || cit.metadata?.page_number) && (
                    <span className="px-1.5 py-0.2 text-[9px] font-semibold text-primary-light bg-primary-soft rounded border border-primary-border">
                      p.{cit.page_number || cit.metadata?.page_number}
                    </span>
                  )}
                  {cit.source === 'ocr' && (
                    <span className="px-1.5 py-0.2 text-[9px] font-semibold uppercase tracking-wider bg-warning-soft text-warning-text rounded border border-warning-border">
                      OCR
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