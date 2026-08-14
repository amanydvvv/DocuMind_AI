import { useCallback, useEffect, useMemo, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { buildDocumentFileRequest } from '../../services/api';
import Icon from '../shared/Icon';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

function ErrorState({ message, onRetry, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200 select-none">
      <div className="glass-card-elevated rounded-2xl w-full max-w-md p-6 text-center animate-in zoom-in-95 duration-200">
        <div className="w-10 h-10 bg-danger-soft text-danger rounded-full flex items-center justify-center mx-auto mb-3 border border-danger-border">
          <Icon name="warning" size={20} />
        </div>
        <h3 className="font-semibold text-text text-sm">Document unavailable</h3>
        <p className="text-xs text-text-muted mt-1.5 mb-5 whitespace-pre-wrap">{message}</p>
        <div className="flex justify-center gap-2">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-hover transition-all duration-150 tactile-btn cursor-pointer"
          >
            Retry
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-surface-muted hover:bg-surface border border-border text-text text-xs font-medium rounded-xl transition-all duration-150 tactile-btn cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * PdfViewer — document citation viewer.
 * Opens the document owned by the current user (authenticated fetch from
 * /api/documents/:id/file) and lands directly on the cited page number.
 * Missing files / deleted documents surface a visible error state.
 */
export default function PdfViewer({
  documentId,
  filename = 'Document',
  pageNumber = 1,
  onClose,
}) {
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(() => Math.max(1, Number(pageNumber) || 1));
  const [loadError, setLoadError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  const file = useMemo(() => buildDocumentFileRequest(documentId), [documentId]);

  useEffect(() => {
    setPage(Math.max(1, Number(pageNumber) || 1));
  }, [pageNumber]);

  const handleLoadSuccess = useCallback(({ numPages: n }) => {
    setNumPages(n);
    setPage((p) => Math.min(p || 1, n));
  }, []);

  const handleLoadError = useCallback((err) => {
    setLoadError(err?.message || 'Document failed to load.');
  }, []);

  if (loadError) {
    return (
      <ErrorState
        message={loadError}
        onRetry={() => {
          setLoadError(null);
          setAttempt((a) => a + 1);
        }}
        onClose={onClose}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-150 select-none">
      <div className="glass-card-elevated rounded-3xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-3.5 border-b border-border flex justify-between items-center bg-surface/50">
          <div className="flex items-center gap-2 min-w-0 pr-4">
            <Icon name="docs" size={15} className="text-primary-light flex-shrink-0" />
            <h3 className="font-semibold text-text text-sm truncate tracking-tight">{filename}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-text-muted hover:text-text hover:bg-surface-muted rounded-lg transition-colors cursor-pointer"
            aria-label="Close PDF viewer"
          >
            <Icon name="x" size={15} />
          </button>
        </div>

        {/* Page navigation bar */}
        {numPages > 0 && (
          <div className="px-6 py-2 flex items-center justify-between bg-surface/70 border-b border-border text-xs">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!page || page <= 1}
              className="px-3 py-1 text-xs font-medium bg-surface-muted text-text rounded-lg hover:bg-surface-elevated disabled:opacity-30 transition-all tactile-btn cursor-pointer"
            >
              ← Prev
            </button>
            <span className="text-[11px] font-medium text-text-secondary" data-testid="page-indicator">
              Page {page} of {numPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(numPages, p + 1))}
              disabled={!page || page >= numPages}
              className="px-3 py-1 text-xs font-medium bg-surface-muted text-text rounded-lg hover:bg-surface-elevated disabled:opacity-30 transition-all tactile-btn cursor-pointer"
            >
              Next →
            </button>
          </div>
        )}

        {/* PDF canvas */}
        <div className="flex-1 overflow-auto bg-background/90 p-6 flex justify-center">
          <Document
            key={`${documentId}:${attempt}`}
            file={file}
            onLoadSuccess={handleLoadSuccess}
            onLoadError={handleLoadError}
            className="shadow-2xl rounded-lg overflow-hidden"
          >
            {page && <Page pageNumber={page} />}
          </Document>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-surface/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-surface-muted hover:bg-surface-elevated border border-border text-text text-xs font-medium rounded-xl transition-all tactile-btn cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}