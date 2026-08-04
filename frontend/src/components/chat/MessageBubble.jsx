import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div 
        className={`max-w-[80%] rounded-2xl px-5 py-4 shadow-sm ${
          isUser 
            ? 'bg-primary text-white rounded-br-sm' 
            : 'bg-white border border-border text-text rounded-bl-sm'
        }`}
      >
        <div className={`prose ${isUser ? 'prose-invert' : 'prose-slate'} max-w-none text-sm`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
        
        {/* Render Citations if they exist and it's an AI message */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <p className="text-xs font-semibold text-text-muted mb-2 uppercase tracking-wide">Sources</p>
            <div className="flex flex-wrap gap-2">
              {message.citations.map((cit, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick && onCitationClick(cit)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-md transition-colors border border-blue-100"
                  title={cit.source === 'ocr' ? 'Text read from a scanned image by a vision model' : `Score: ${cit.score?.toFixed(3)}`}
                >
                  📄 {cit.filename || cit.metadata?.filename || 'Document'}
                  {cit.source === 'ocr' && (
                    <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-700 rounded border border-amber-200">
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
