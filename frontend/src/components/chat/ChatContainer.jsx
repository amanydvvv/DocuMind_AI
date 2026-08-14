import { Suspense, lazy, useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import CitationViewer from '../shared/CitationViewer';
import Icon from '../shared/Icon';

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
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      {/* Hardware Studio Header */}
      <header className="h-14 px-6 border-b border-border bg-surface flex items-center justify-between z-10 select-none shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
          <h1 className="text-sm font-semibold text-text truncate max-w-md tracking-tight">
            {activeConversation?.title || 'New Research Thread'}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted border border-border text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span className="font-medium text-text">◈ Hybrid RAG</span>
            <span className="text-text-muted/60">•</span>
            <span className="text-primary-light font-medium">Cascade LLM</span>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-danger-soft/90 backdrop-blur-sm border-b border-danger-border text-danger-text px-4 py-2.5 text-xs flex justify-between items-center gap-3 animate-in slide-in-from-top-2 duration-150">
          <span className="flex items-center gap-2 font-medium">
            <Icon name="warning" size={14} className="text-danger" />
            {error}
          </span>
          {onDismissError && (
            <button
              onClick={onDismissError}
              className="p-1 text-danger-text/70 hover:text-danger-text hover:bg-white/10 rounded-md transition-colors cursor-pointer"
              aria-label="Dismiss error"
              title="Dismiss"
            >
              <Icon name="x" size={12} />
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

      {/* Floating Chat Input Dock */}
      <div className="p-4 md:p-6 bg-gradient-to-t from-background via-background/90 to-transparent">
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

      {/* PDF Viewer Overlay (lazy loaded) */}
      {activePdf && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
              <div className="glass-card-elevated rounded-2xl px-6 py-5 shadow-2xl flex flex-col items-center">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
                <p className="text-xs font-medium text-text-muted">Loading PDF Engine...</p>
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