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
    <div className="flex flex-col h-full relative overflow-hidden" style={{ background: 'transparent' }}>

      {/* ── Header ── */}
      <header
        className="h-14 px-6 flex items-center justify-between z-10 flex-shrink-0"
        style={{
          background: 'rgba(8,9,13,0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          boxShadow: '0 1px 24px rgba(0,0,0,0.4)',
        }}
      >
        <div className="flex items-center gap-3 min-w-0">
          {/* Live pulse indicator */}
          <div className="relative flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <div className="absolute inset-0 rounded-full bg-amber-400 animate-ping opacity-40" />
          </div>
          <h1
            className={`text-sm font-semibold truncate max-w-xs md:max-w-md tracking-tight ${isGenerating ? 'text-amber-300' : 'text-slate-100'}`}
            style={{ transition: 'color 0.3s ease' }}
          >
            {activeConversation?.title || 'New Research Thread'}
          </h1>
        </div>

        {/* Status pill */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px]"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: isGenerating ? '#f59e0b' : '#34d399',
              boxShadow: isGenerating ? '0 0 6px rgba(245,158,11,0.8)' : '0 0 6px rgba(52,211,153,0.8)',
              animation: isGenerating ? 'pulse 0.8s ease-in-out infinite' : 'none',
            }}
          />
          <span className="font-medium" style={{ color: '#94a3b8' }}>◈ Hybrid RAG</span>
          <span style={{ color: 'rgba(148,163,184,0.4)' }}>•</span>
          <span className="font-semibold" style={{ color: '#fde68a' }}>Cascade LLM</span>
        </div>
      </header>

      {/* ── Error Banner ── */}
      {error && (
        <div
          className="px-5 py-2.5 text-xs flex justify-between items-center gap-3 flex-shrink-0"
          style={{
            background: 'rgba(255,69,58,0.1)',
            borderBottom: '1px solid rgba(255,69,58,0.2)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span className="flex items-center gap-2 font-medium" style={{ color: '#fca5a5' }}>
            <Icon name="warning" size={13} />
            {error}
          </span>
          {onDismissError && (
            <button
              onClick={onDismissError}
              className="p-1 rounded-md transition-colors cursor-pointer hover:bg-white/10"
              style={{ color: 'rgba(252,165,165,0.6)' }}
              aria-label="Dismiss error"
            >
              <Icon name="x" size={12} />
            </button>
          )}
        </div>
      )}

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <MessageList
          messages={messages}
          isLoadingHistory={isLoadingHistory}
          isGenerating={isGenerating}
          onCitationClick={setActiveCitation}
          onSendMessage={onSendMessage}
        />
      </div>

      {/* ── Input Dock ── */}
      <div
        className="p-4 md:p-5 flex-shrink-0"
        style={{
          background: 'linear-gradient(to top, rgba(8,9,13,1) 60%, rgba(8,9,13,0) 100%)',
        }}
      >
        <ChatInput onSendMessage={onSendMessage} disabled={isGenerating || isLoadingHistory} />
      </div>

      {/* ── Citation Modal ── */}
      {activeCitation && (
        <CitationViewer
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
          onViewDocument={handleViewDocument}
        />
      )}

      {/* ── PDF Viewer ── */}
      {activePdf && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md">
              <div
                className="rounded-2xl px-6 py-5 flex flex-col items-center gap-3"
                style={{ background: 'rgba(24,27,35,0.95)', border: '1px solid rgba(255,255,255,0.1)' }}
              >
                <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
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