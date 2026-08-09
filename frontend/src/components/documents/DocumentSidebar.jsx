import { useState, useEffect } from 'react';
import { fetchDocuments, deleteDocument } from '../../services/api';
import UploadPanel from './UploadPanel';
import Icon from '../shared/Icon';

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
    <div className="w-80 h-full bg-surface border-r border-border flex flex-col p-4 overflow-y-auto">
      <h2 className="text-lg font-semibold text-text mb-4">Knowledge Base</h2>
      
      <UploadPanel onUploadComplete={loadDocuments} />

      <div className="flex-1">
        <h3 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-3">
          Documents ({documents.length})
        </h3>
        
        {isLoading ? (
          <p className="text-sm text-text-muted">Loading...</p>
        ) : error ? (
          <p className="text-sm text-danger-text">{error}</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-text-muted">No documents uploaded yet.</p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.id} className="p-3 border border-border rounded-lg bg-background hover:border-primary/60 transition-colors group">
                <div className="flex justify-between items-start mb-1">
                  <h4 className="text-sm font-medium text-text truncate pr-2" title={doc.filename}>
                    {doc.filename}
                  </h4>
                  <button 
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-text-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50 flex-shrink-0"
                    aria-label={`Delete document: ${doc.filename}`}
                    title="Delete document"
                  >
                    <Icon name="trash" size={15} />
                  </button>
                </div>
                
                <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                  <span className={`px-1.5 py-0.5 rounded-sm font-medium ${
                    doc.status === 'completed' ? 'bg-success-soft text-success-text' :
                    doc.status === 'error' ? 'bg-danger-soft text-danger-text' :
                    'bg-warning-soft text-warning-text'
                  }`}>
                    {doc.status}
                  </span>
                  <span>• {formatFileSize(doc.file_size)}</span>
                </div>
                
                <div className="flex gap-3 text-xs text-text-muted">
                  <span className="flex items-center gap-1" title="Page count">
                    <Icon name="docs" size={13} />
                    {doc.page_count || 0} pgs
                  </span>
                  <span className="flex items-center gap-1" title="Vector chunks">
                    <Icon name="grid" size={13} />
                    {doc.chunk_count || 0} chunks
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}