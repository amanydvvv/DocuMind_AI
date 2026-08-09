import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Icon from '../shared/Icon';

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div 
        className={`max-w-[80%] rounded-2xl px-5 py-4 shadow-sm ${
          isUser 
            ? 'bg-primary text-white rounded-br-sm' 
            : 'bg-surface border border-border text-text rounded-bl-sm'
        }`}
      >
        <div className={`markdown max-w-none text-sm ${isUser ? '' : ''}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
        
        {/* Render Citations if they exist and it's an AI message */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border-subtle">
            <p className="text-xs font-semibold text-text-muted mb-2 uppercase tracking-wide">Sources</p>
            <div className="flex flex-wrap gap-2">
              {message.citations.map((cit, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick && onCitationClick(cit)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-primary-soft text-primary-light hover:bg-primary-border rounded-md transition-colors border border-primary-border"
                  title={cit.source === 'ocr' ? 'Text read from a scanned image by a vision model' : `Score: ${cit.score?.toFixed(3)}`}
                >
                  <Icon name="docs" size={13} />
                  {cit.filename || cit.metadata?.filename || 'Document'}
                  {(cit.page_number || cit.metadata?.page_number) && (
                    <span className="px-1.5 py-0.5 text-[10px] font-semibold text-primary-light bg-surface rounded border border-primary-border">
                      p.{cit.page_number || cit.metadata?.page_number}
                    </span>
                  )}
                  {cit.source === 'ocr' && (
                    <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-warning-soft text-warning-text rounded border border-warning-border">
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