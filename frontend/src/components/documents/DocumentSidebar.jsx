import { useState, useEffect } from 'react';
import { fetchDocuments, deleteDocument } from '../../lib/api';
import UploadPanel from './UploadPanel';

export default function DocumentSidebar() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

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
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await deleteDocument(documentId);
      loadDocuments();
    } catch (err) {
      alert('Failed to delete document: ' + err.message);
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
                    className="text-text-muted hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete document"
                  >
                    ✕
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
