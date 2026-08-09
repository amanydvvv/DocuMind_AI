import { Suspense, lazy, useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import CitationViewer from '../shared/CitationViewer';

const PdfViewer = lazy(() => import('../pdf/PdfViewer'));

export default function ChatContainer({
  activeConversation,
  messages,
  isLoadingHistory,
  isGenerating,
  error,
  onSendMessage,
  onDismissError,
}) {
  const [activeCitation, setActiveCitation] = useState(null);
  const [activePdf, setActivePdf] = useState(null);

  const handleViewDocument = (citation) => {
    setActiveCitation(null);
    setActivePdf({
      documentId: citation.document_id,
      filename: citation.filename || citation.metadata?.filename || 'Document',
      pageNumber: citation.page_number || citation.metadata?.page_number || 1,
    });
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 relative overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-border p-4 flex items-center justify-between shadow-sm z-10">
        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 truncate max-w-md">
          {activeConversation?.title || 'New Chat'}
        </h1>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 text-red-700 px-4 py-2 text-xs flex justify-between items-center gap-3">
          <span>⚠️ {error}</span>
          {onDismissError && (
            <button
              onClick={onDismissError}
              className="flex-shrink-0 px-1.5 text-red-400 hover:text-red-700 hover:bg-red-100 rounded transition-colors"
              aria-label="Dismiss error"
              title="Dismiss"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <MessageList
          messages={messages}
          isLoadingHistory={isLoadingHistory}
          isGenerating={isGenerating}
          onCitationClick={setActiveCitation}
          onSendMessage={onSendMessage}
        />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-border">
        <ChatInput onSendMessage={onSendMessage} disabled={isGenerating || isLoadingHistory} />
      </div>

      {/* Citation Modal Overlay */}
      {activeCitation && (
        <CitationViewer
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
          onViewDocument={handleViewDocument}
        />
      )}

      {/* PDF Viewer Overlay (lazy: pdf.js chunk loads on first open) */}
      {activePdf && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="bg-white rounded-xl px-6 py-4 shadow-xl animate-in zoom-in-95 duration-200">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-sm font-medium text-text-muted">Loading PDF viewer...</p>
              </div>
            </div>
          }
        >
          <PdfViewer
            key={activePdf.documentId}
            documentId={activePdf.documentId}
            filename={activePdf.filename}
            pageNumber={activePdf.pageNumber}
            onClose={() => setActivePdf(null)}
          />
        </Suspense>
      )}
    </div>
  );
}