import { useState, useEffect } from 'react';
import { fetchDocuments, deleteDocument } from '../../services/api';
import UploadPanel from './UploadPanel';

export default function DocumentSidebar() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents || []);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleDelete = async (documentId) => {
    if (deletingId) return; // prevent double-click
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    // Snapshot for rollback
    const snapshot = documents;

    // Optimistic removal
    setDeletingId(documentId);
    setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    setError('');

    try {
      await deleteDocument(documentId);
    } catch (err) {
      // Rollback on failure
      setDocuments(snapshot);
      setError('Failed to delete document: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-80 h-full bg-white border-r border-border flex flex-col p-4 overflow-y-auto">
      <h2 className="text-lg font-semibold text-text mb-4">Knowledge Base</h2>
      
      <UploadPanel onUploadComplete={loadDocuments} />

      <div className="flex-1">
        <h3 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-3">
          Documents ({documents.length})
        </h3>
        
        {isLoading ? (
          <p className="text-sm text-text-muted">Loading...</p>
        ) : error ? (
          <p className="text-sm text-red-500">{error}</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-text-muted">No documents uploaded yet.</p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.id} className="p-3 border border-border rounded-lg bg-background hover:border-primary/50 transition-colors group">
                <div className="flex justify-between items-start mb-1">
                  <h4 className="text-sm font-medium text-text truncate pr-2" title={doc.filename}>
                    {doc.filename}
                  </h4>
                  <button 
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-text-muted hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50 flex-shrink-0"
                    aria-label="Delete document"
                    title="Delete document"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  </button>
                </div>
                
                <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                  <span className={`px-1.5 py-0.5 rounded-sm font-medium ${
                    doc.status === 'completed' ? 'bg-green-100 text-green-700' :
                    doc.status === 'error' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {doc.status}
                  </span>
                  <span>• {formatFileSize(doc.file_size)}</span>
                </div>
                
                <div className="flex gap-3 text-xs text-text-muted">
                  <span title="Page count">📄 {doc.page_count || 0} pgs</span>
                  <span title="Vector chunks">🧩 {doc.chunk_count || 0} chunks</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
