import Icon from './Icon';

export default function CitationViewer({ citation, onClose, onViewDocument }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150 select-none">
      <div className="glass-card-elevated rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-surface">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-primary text-sm font-bold">◈</span>
              <h3 className="font-semibold text-text text-sm tracking-tight">
                {citation.filename || citation.metadata?.filename || 'Document Source'}
              </h3>
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-[11px] text-text-muted">
              {(citation.page_number || citation.metadata?.page_number) && (
                <span className="flex items-center gap-1 font-medium text-text-secondary">
                  Page {citation.page_number || citation.metadata?.page_number}
                </span>
              )}
              {citation.source === 'ocr' && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.2 font-semibold uppercase tracking-wider bg-amber-500/15 text-amber-300 rounded border border-amber-500/30 text-[9px]">
                  <span>◬</span>
                  <span>OCR Vision Scan</span>
                </span>
              )}
              {citation.score !== undefined && citation.score !== null && (
                <span className="flex items-center gap-1 text-text-secondary font-medium">
                  <span className="text-emerald-400">▣</span>
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

        {/* Recessed Monospace Terminal Well */}
        <div className="p-6 overflow-y-auto flex-1 text-[13px] leading-relaxed text-text select-text bg-surface/50">
          <div className="recessed-well p-4 rounded-xl font-mono text-xs text-amber-100/90 whitespace-pre-wrap leading-relaxed">
            {citation.content_preview || citation.content}
          </div>
        </div>
        
        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-border bg-surface flex justify-end gap-2.5">
          {onViewDocument && citation.document_id && (
            <button
              onClick={() => onViewDocument(citation)}
              className="px-4 py-2 clay-btn text-xs rounded-xl flex items-center gap-1.5 cursor-pointer"
            >
              <span className="text-[11px]">▣</span>
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