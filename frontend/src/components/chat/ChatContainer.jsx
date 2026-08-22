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
  onOpenMobileMenu,
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
        className="h-14 px-3 sm:px-6 flex items-center justify-between z-10 flex-shrink-0"
        style={{
          background: 'linear-gradient(180deg, rgba(9, 20, 16, 0.85) 0%, rgba(5, 13, 8, 0.9) 100%)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 4px 30px rgba(0, 0, 0, 0.5)',
        }}
      >
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {/* Mobile menu hamburger button */}
          <button
            type="button"
            onClick={onOpenMobileMenu}
            className="md:hidden p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer flex-shrink-0"
            aria-label="Open navigation sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>

          {/* Header thread indicator (outline style) */}
          <div className="relative flex-shrink-0 hidden sm:flex items-center justify-center">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{
                background: 'transparent',
                border: '1.5px solid #00d68f',
                boxShadow: '0 0 8px rgba(0, 214, 143, 0.35)',
              }}
            />
          </div>
          <h1
            className={`text-xs sm:text-sm font-bold truncate max-w-[130px] sm:max-w-xs md:max-w-md tracking-tight ${isGenerating ? 'text-emerald-300' : 'text-white'}`}
            style={{ transition: 'color 0.3s ease' }}
          >
            {activeConversation?.title || 'New Research Thread'}
          </h1>
        </div>

        {/* Status pill — Glassmorphic & Responsive on Mobile */}
        <div
          className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, rgba(13, 29, 21, 0.8) 0%, rgba(9, 20, 16, 0.85) 100%)',
            border: '1px solid rgba(0, 214, 143, 0.28)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: '0 2px 12px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: isGenerating ? '#00ffaa' : '#00d68f',
              boxShadow: isGenerating ? '0 0 8px rgba(0,255,170,1)' : '0 0 6px rgba(0,214,143,0.8)',
              animation: isGenerating ? 'pulse 0.8s ease-in-out infinite' : 'none',
            }}
          />
          <span className="hidden sm:inline font-semibold text-slate-200" title="Combines vector similarity and keyword (BM25) search for better document retrieval accuracy">◈ Hybrid RAG</span>
          <span className="hidden sm:inline text-white/20">•</span>
          <span className="font-bold text-emerald-400" title="Uses a primary LLM with automatic fallback to backup models if rate-limited">Cascade LLM</span>
        </div>
      </header>

      {/* ── Error Banner ── */}
      {error && (
        <div
          className="px-4 sm:px-5 py-2.5 text-xs flex justify-between items-center gap-3 flex-shrink-0"
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
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-8">
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
        className="p-2.5 sm:p-4 md:p-5 flex-shrink-0"
        style={{
          background: 'linear-gradient(to top, rgba(5,13,8,1) 60%, rgba(5,13,8,0) 100%)',
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
                <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#00d68f', borderTopColor: 'transparent' }} />
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