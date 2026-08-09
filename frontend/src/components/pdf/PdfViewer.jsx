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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface rounded-2xl shadow-xl w-full max-w-md p-6 text-center animate-in zoom-in-95 duration-200">
        <div className="w-12 h-12 bg-danger-soft text-danger rounded-full flex items-center justify-center mx-auto mb-3">
          <Icon name="warning" size={26} />
        </div>
        <h3 className="font-semibold text-text text-lg">Document unavailable</h3>
        <p className="text-sm text-text-muted mt-1 mb-5 whitespace-pre-wrap">{message}</p>
        <div className="flex justify-center gap-2">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-hover transition-colors"
          >
            Retry
          </button>
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-surface-muted/40">
          <h3 className="font-semibold text-text text-lg truncate">{filename}</h3>
          <button
            onClick={onClose}
            className="p-2 text-text-muted hover:text-text hover:bg-surface-muted rounded-full transition-colors"
            aria-label="Close PDF viewer"
          >
            <Icon name="x" size={16} />
          </button>
        </div>

        {/* Page navigation */}
        {numPages > 0 && (
          <div className="px-6 py-2 flex items-center justify-between bg-surface border-b border-border">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!page || page <= 1}
              className="px-3 py-1 text-xs font-medium bg-surface-muted text-text rounded-md hover:bg-border disabled:opacity-40 transition-colors"
            >
              ← Prev
            </button>
            <span className="text-xs font-medium text-text-muted" data-testid="page-indicator">
              Page {page} of {numPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(numPages, p + 1))}
              disabled={!page || page >= numPages}
              className="px-3 py-1 text-xs font-medium bg-surface-muted text-text rounded-md hover:bg-border disabled:opacity-40 transition-colors"
            >
              Next →
            </button>
          </div>
        )}

        {/* PDF canvas */}
        <div className="flex-1 overflow-auto bg-surface-muted p-4">
          <Document
            key={`${documentId}:${attempt}`}
            file={file}
            onLoadSuccess={handleLoadSuccess}
            onLoadError={handleLoadError}
          >
            {page && <Page pageNumber={page} />}
          </Document>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-surface-muted/40 flex justify-end">
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