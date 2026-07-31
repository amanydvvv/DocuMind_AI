export default function CitationViewer({ citation, onClose }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-gray-50/50">
          <div>
            <h3 className="font-semibold text-text text-lg">
              {citation.filename || citation.metadata?.filename || 'Document Source'}
            </h3>
            <div className="flex gap-3 mt-1 text-xs text-text-muted">
              {(citation.page_number || citation.metadata?.page_number) && (
                <span className="flex items-center gap-1">
                  📄 Page {citation.page_number || citation.metadata?.page_number}
                </span>
              )}
              {citation.score !== undefined && citation.score !== null && (
                <span className="flex items-center gap-1">
                  🎯 Relevance: {(citation.score * 100).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-text-muted hover:text-text hover:bg-gray-100 rounded-full transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 text-sm leading-relaxed text-text bg-yellow-50/30">
          <div className="prose prose-slate max-w-none border-l-4 border-blue-400 pl-4 py-1 text-gray-800 whitespace-pre-wrap">
            {citation.content_preview || citation.content}
          </div>
        </div>
        
        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-gray-50 flex justify-end">
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-white border border-border text-text text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
