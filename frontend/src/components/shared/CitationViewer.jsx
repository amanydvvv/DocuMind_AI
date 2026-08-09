import Icon from './Icon';

export default function CitationViewer({ citation, onClose, onViewDocument }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-surface-muted/40">
          <div>
            <h3 className="font-semibold text-text text-lg">
              {citation.filename || citation.metadata?.filename || 'Document Source'}
            </h3>
            <div className="flex gap-3 mt-1 text-xs text-text-muted">
              {(citation.page_number || citation.metadata?.page_number) && (
                <span className="flex items-center gap-1">
                  <Icon name="docs" size={14} />
                  Page {citation.page_number || citation.metadata?.page_number}
                </span>
              )}
              {citation.source === 'ocr' && (
                <span className="inline-flex items-center px-1.5 py-0.5 font-semibold uppercase tracking-wide bg-warning-soft text-warning-text rounded border border-warning-border">
                  Read from image (OCR)
                </span>
              )}
              {citation.score !== undefined && citation.score !== null && (
                <span className="flex items-center gap-1">
                  <Icon name="target" size={14} />
                  Relevance: {(citation.score * 100).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-text-muted hover:text-text hover:bg-surface-muted rounded-full transition-colors"
            aria-label="Close citation viewer"
          >
            <Icon name="x" size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 text-sm leading-relaxed text-text bg-warning-soft/50">
          <div className="markdown max-w-none border-l-4 border-warning pl-4 py-1 text-text whitespace-pre-wrap">
            {citation.content_preview || citation.content}
          </div>
        </div>
        
        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-surface-muted/40 flex justify-end gap-2">
          {onViewDocument && citation.document_id && (
            <button
              onClick={() => onViewDocument(citation)}
              className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-hover transition-colors shadow-sm flex items-center gap-1.5"
            >
              <Icon name="docs" size={15} />
              View in document
            </button>
          )}
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-surface border border-border text-text text-sm font-medium rounded-lg hover:bg-surface-muted transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}