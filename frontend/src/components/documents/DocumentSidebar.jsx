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
    if (!window.confirm('Delete this document from the knowledge base?')) return;

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
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="flex flex-col h-full p-4 overflow-y-auto space-y-4">
      {/* Upload Zone */}
      <UploadPanel onUploadComplete={loadDocuments} />

      {/* Indexed Library Section */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between px-1 py-1 mb-2">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <span className="text-primary text-[10px]">▣</span>
            <span>Indexed Corpus</span>
          </span>
          <span className="text-[10px] font-bold text-emerald-300 px-2 py-0.5 rounded-full bg-primary-soft border border-primary-border">
            {documents.length}
          </span>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : error ? (
          <div className="p-3 rounded-xl bg-danger-soft border border-danger-border text-danger-text text-xs">
            {error}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 px-2 border border-dashed border-white/10 rounded-xl bg-surface/30 backdrop-blur-xs">
            <p className="text-xs text-slate-300 font-medium">No documents uploaded yet.</p>
            <p className="text-[11px] text-slate-400 mt-1">Upload PDF, TXT, or MD files above to enable grounding.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div 
                key={doc.id} 
                className="group relative p-3 rounded-xl transition-all duration-150 shadow-sm"
                style={{
                  background: 'linear-gradient(145deg, rgba(13, 29, 21, 0.75) 0%, rgba(9, 20, 16, 0.85) 100%)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
                }}
              >
                <div className="flex justify-between items-start gap-2 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-6 h-6 rounded-lg bg-surface-muted flex items-center justify-center flex-shrink-0 text-emerald-400 border border-white/10 text-[11px]">
                      ▣
                    </div>
                    <h4 className="text-xs font-semibold text-white truncate" title={doc.filename}>
                      {doc.filename}
                    </h4>
                  </div>
                  <button 
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-slate-400 hover:text-danger-text hover:bg-danger-soft p-1 rounded-md opacity-0 group-hover:opacity-100 transition-all duration-150 disabled:opacity-40 flex-shrink-0 cursor-pointer"
                    aria-label={`Delete document: ${doc.filename}`}
                    title="Delete document"
                  >
                    <Icon name="trash" size={13} />
                  </button>
                </div>
                
                <div className="flex items-center justify-between text-[10px] text-text-muted pt-1 border-t border-border-subtle">
                  <div className="flex items-center gap-1.5">
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full font-medium ${
                      doc.status === 'completed' ? 'bg-success-soft text-success-text border border-success-border' :
                      doc.status === 'error' ? 'bg-danger-soft text-danger-text border border-danger-border' :
                      'bg-warning-soft text-warning-text border border-warning-border'
                    }`}>
                      <span className={`w-1 h-1 rounded-full ${
                        doc.status === 'completed' ? 'bg-success' :
                        doc.status === 'error' ? 'bg-danger' :
                        'bg-warning animate-ping'
                      }`}></span>
                      {doc.status}
                    </span>
                    <span>{formatFileSize(doc.file_size)}</span>
                  </div>
                  
                  <div className="flex items-center gap-2 text-text-muted">
                    <span title="Page count">
                      {doc.page_count || 1} pgs
                    </span>
                    <span>•</span>
                    <span title="Vector chunks">
                      {doc.chunk_count || 0} chunks
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}