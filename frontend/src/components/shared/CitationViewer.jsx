import Icon from './Icon';

export default function CitationViewer({ citation, onClose, onViewDocument }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-150 select-none">
      <div className="glass-card-elevated rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-surface/40">
          <div>
            <div className="flex items-center gap-2">
              <Icon name="docs" size={15} className="text-primary-light" />
              <h3 className="font-semibold text-text text-sm tracking-tight">
                {citation.filename || citation.metadata?.filename || 'Document Source'}
              </h3>
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-[11px] text-text-muted">
              {(citation.page_number || citation.metadata?.page_number) && (
                <span className="flex items-center gap-1">
                  Page {citation.page_number || citation.metadata?.page_number}
                </span>
              )}
              {citation.source === 'ocr' && (
                <span className="inline-flex items-center px-1.5 py-0.2 font-semibold uppercase tracking-wider bg-warning-soft text-warning-text rounded border border-warning-border text-[9px]">
                  OCR Vision Scan
                </span>
              )}
              {citation.score !== undefined && citation.score !== null && (
                <span className="flex items-center gap-1 text-text-secondary">
                  <Icon name="target" size={11} className="text-emerald-400" />
                  Score: {(citation.score * 100).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-text-muted hover:text-text hover:bg-surface-muted rounded-lg transition-colors cursor-pointer"
            aria-label="Close citation viewer"
          >
            <Icon name="x" size={15} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 text-[13px] leading-relaxed text-text select-text bg-surface/30">
          <div className="p-4 rounded-xl bg-background/60 border border-border-subtle font-mono text-xs text-text-secondary whitespace-pre-wrap leading-relaxed shadow-inner">
            {citation.content_preview || citation.content}
          </div>
        </div>
        
        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-border bg-surface/40 flex justify-end gap-2">
          {onViewDocument && citation.document_id && (
            <button
              onClick={() => onViewDocument(citation)}
              className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-hover transition-all duration-150 shadow-sm flex items-center gap-1.5 tactile-btn cursor-pointer"
            >
              <Icon name="docs" size={13} />
              <span>View in document</span>
            </button>
          )}
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-surface-muted hover:bg-surface-elevated border border-border text-text text-xs font-medium rounded-xl transition-all duration-150 tactile-btn cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}