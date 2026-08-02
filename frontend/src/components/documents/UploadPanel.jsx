import { useState, useRef } from 'react';
import { uploadDocument, getDocument } from '../../lib/api';

export default function UploadPanel({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState('idle'); // idle | uploading | polling | error
  const [errorMessage, setErrorMessage] = useState('');
  const [currentFile, setCurrentFile] = useState(null);
  const fileInputRef = useRef(null);
  const pollAttemptsRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 90; // ~3 minutes at 2s intervals

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file) => {
    setCurrentFile(file);
    setUploadState('uploading');
    setErrorMessage('');

    try {
      const doc = await uploadDocument(file);
      if (doc.status === 'completed' || doc.status === 'error') {
        if (doc.status === 'error') {
          setUploadState('error');
          setErrorMessage(doc.error_message || 'Ingestion failed');
        } else {
          setUploadState('idle');
          setCurrentFile(null);
          onUploadComplete();
        }
        return;
      }
      
      // Polling
      setUploadState('polling');
      pollAttemptsRef.current = 0;
      pollDocumentStatus(doc.id);
    } catch (err) {
      setUploadState('error');
      setErrorMessage(err.message);
    }
  };

  const pollDocumentStatus = async (documentId) => {
    pollAttemptsRef.current += 1;
    try {
      const doc = await getDocument(documentId);
      if (doc.status === 'completed') {
        setUploadState('idle');
        setCurrentFile(null);
        onUploadComplete();
      } else if (doc.status === 'error') {
        setUploadState('error');
        setErrorMessage(doc.error_message || 'Ingestion failed');
      } else if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
        setUploadState('error');
        setErrorMessage('Timed out waiting for processing. Check the document list and retry if needed.');
      } else {
        // Still pending/processing
        setTimeout(() => pollDocumentStatus(documentId), 2000);
      }
    } catch (err) {
      setUploadState('error');
      setErrorMessage(err.message);
    }
  };

  return (
    <div className="mb-6">
      <div 
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors
          ${isDragging ? 'border-primary bg-blue-50' : 'border-border'}
          ${uploadState === 'error' ? 'border-red-400 bg-red-50' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileSelect} 
          className="hidden" 
          accept=".pdf,.md,.txt" 
        />
        
        {uploadState === 'idle' && (
          <div className="cursor-pointer" onClick={() => fileInputRef.current?.click()}>
            <p className="text-sm font-medium text-text">Drag & drop a file here</p>
            <p className="text-xs text-text-muted mt-1">or click to browse (.pdf, .md)</p>
          </div>
        )}

        {uploadState === 'uploading' && (
          <div>
            <p className="text-sm font-medium text-text animate-pulse">Uploading {currentFile?.name}...</p>
          </div>
        )}

        {uploadState === 'polling' && (
          <div>
            <p className="text-sm font-medium text-text animate-pulse">Processing {currentFile?.name}...</p>
            <p className="text-xs text-text-muted mt-1">Chunking and embedding document...</p>
          </div>
        )}

        {uploadState === 'error' && (
          <div>
            <p className="text-sm font-medium text-red-600">Error uploading {currentFile?.name}</p>
            <p className="text-xs text-red-500 mt-1">{errorMessage}</p>
            <button 
              className="mt-3 text-xs bg-red-100 hover:bg-red-200 text-red-700 py-1 px-3 rounded transition-colors"
              onClick={() => { setUploadState('idle'); setErrorMessage(''); setCurrentFile(null); }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
