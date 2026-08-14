import { useState, useRef, useReducer, useEffect } from 'react';
import { uploadDocument, getDocument } from '../../services/api';

export default function UploadPanel({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Queue reducer and initial state
  const initialState = [];
  function reducer(state, action) {
    switch (action.type) {
      case 'ENQUEUE':
        return [...state, action.item];
      case 'SET_STATUS':
        return state.map(i => i.id === action.id ? { ...i, status: action.status } : i);
      case 'SET_ERROR':
        return state.map(i => i.id === action.id ? { ...i, status: 'error', errorMessage: action.errorMessage } : i);
      case 'SET_DOCUMENT_ID':
        return state.map(i => i.id === action.id ? { ...i, documentId: action.documentId } : i);
      case 'RETRY':
        return state.map(i => i.id === action.id ? { ...i, status: 'queued', retryCount: (i.retryCount || 0) + 1, errorMessage: null } : i);
      case 'CLEAR_FINISHED':
        return state.filter(i => i.status !== 'completed' && !(i.status === 'error' && i.retryCount >= 3));
      default:
        return state;
    }
  }

  const [fileQueue, dispatch] = useReducer(reducer, initialState);
  const [hasCompletedCallback, setHasCompletedCallback] = useState(false);

  const MAX_POLL_ATTEMPTS = 90; // existing constant
  const MAX_CONCURRENT_UPLOADS = 2;
  const allowedExtensions = new Set(['pdf', 'md', 'txt']);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      enqueueFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      enqueueFiles(e.target.files);
    }
  };

  function enqueueFiles(fileList) {
    Array.from(fileList).forEach((file) => {
      if (file.size === 0) return; // skip zero‑byte files
      const ext = file.name.split('.').pop().toLowerCase();
      if (!allowedExtensions.has(ext)) {
        const id = crypto.randomUUID();
        dispatch({
          type: 'ENQUEUE',
          item: { id, file, name: file.name, size: file.size, status: 'error', errorMessage: 'Unsupported file type', retryCount: 0 }
        });
        return;
      }
      const id = crypto.randomUUID();
      dispatch({
        type: 'ENQUEUE',
        item: { id, file, name: file.name, size: file.size, status: 'queued', errorMessage: null, documentId: null, retryCount: 0 }
      });
    });
  }

  // Process queue respecting concurrency limit
  async function processQueue() {
    const active = fileQueue.filter(i => i.status === 'uploading' || i.status === 'processing').length;
    const available = MAX_CONCURRENT_UPLOADS - active;
    if (available <= 0) return;
    const toStart = fileQueue.filter(i => i.status === 'queued').slice(0, available);
    await Promise.all(toStart.map(item => handleItem(item)));
  }

  async function handleItem(item) {
    dispatch({ type: 'SET_STATUS', id: item.id, status: 'uploading' });
    try {
      const doc = await uploadDocument(item.file);
      dispatch({ type: 'SET_STATUS', id: item.id, status: 'processing' });
      dispatch({ type: 'SET_DOCUMENT_ID', id: item.id, documentId: doc.id });
      await pollDocument(item.id, doc.id, 0);
    } catch (err) {
      const msg = err.message && err.message.toLowerCase().includes('already uploaded')
        ? 'Already uploaded'
        : err.message || 'Upload failed';
      dispatch({ type: 'SET_ERROR', id: item.id, errorMessage: msg });
    }
  }

  async function pollDocument(queueId, documentId, attempt) {
    if (attempt >= MAX_POLL_ATTEMPTS) {
      dispatch({ type: 'SET_ERROR', id: queueId, errorMessage: 'Polling timed out' });
      return;
    }
    try {
      const doc = await getDocument(documentId);
      if (doc.status === 'completed') {
        dispatch({ type: 'SET_STATUS', id: queueId, status: 'completed' });
        return;
      } else if (doc.status === 'error') {
        dispatch({ type: 'SET_ERROR', id: queueId, errorMessage: doc.error_message || 'Ingestion failed' });
        return;
      } else {
        setTimeout(() => pollDocument(queueId, documentId, attempt + 1), 2000);
      }
    } catch (err) {
      dispatch({ type: 'SET_ERROR', id: queueId, errorMessage: err.message || 'Polling failed' });
    }
  }

  // React to queue changes: start workers and fire final callback
  useEffect(() => {
    processQueue();
    if (fileQueue.length > 0 && fileQueue.every(i => i.status === 'completed' || i.status === 'error')) {
      if (!hasCompletedCallback) {
        onUploadComplete();
        setHasCompletedCallback(true);
      }
    } else {
      setHasCompletedCallback(false);
    }
  }, [fileQueue]);

  const handleRetry = (id) => {
    const item = fileQueue.find(i => i.id === id);
    if (item && (item.retryCount || 0) < 3) {
      dispatch({ type: 'RETRY', id });
    }
  };

  const handleClearFinished = () => {
    dispatch({ type: 'CLEAR_FINISHED' });
  };

  return (
    <div className="mb-6">
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${isDragging ? 'border-primary bg-primary-soft' : 'border-border'}`}
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
          multiple
        />
        <div className="cursor-pointer" onClick={() => fileInputRef.current?.click()}>
          <p className="text-sm font-medium text-text">Drag &amp; drop files here</p>
          <p className="text-xs text-text-muted mt-1">or click to browse (.pdf, .md, .txt)</p>
        </div>
      </div>

      {fileQueue.length > 0 && (
        <>
          {/* Overall progress */}
          <div className="text-sm text-text mb-2">
            Processed {fileQueue.filter(i => i.status === 'completed' || i.status === 'error').length}/{fileQueue.length} files
            <div className="w-full bg-gray-soft h-2 rounded mt-1">
              <div
                className="bg-primary-soft h-2 rounded"
                style={{
                  width: `${(fileQueue.filter(i => i.status === 'completed' || i.status === 'error').length / fileQueue.length) * 100}%`,
                }}
              />
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-text">Upload Queue</span>
              <button
                className="text-xs bg-gray-soft hover:bg-gray-border text-gray-text py-1 px-2 rounded"
                onClick={handleClearFinished}
              >
                Clear Finished
              </button>
            </div>
            <ul className="space-y-2">
              {fileQueue.map(item => (
                <li key={item.id} className="flex items-center justify-between p-2 border rounded bg-white">
                  <div className="flex-1 overflow-hidden">
                    <span className="font-medium text-text" title={item.name}>{item.name}</span>
                    <span className="text-xs text-text-muted ml-2">({(item.size / 1024).toFixed(1)}KB)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {item.status === 'queued' && <span className="badge bg-gray-soft text-gray-text">Queued</span>}
                    {item.status === 'uploading' && <span className="badge bg-primary-soft text-primary-text animate-pulse">Uploading</span>}
                    {item.status === 'processing' && <span className="badge bg-warning-soft text-warning-text animate-pulse">Processing</span>}
                    {item.status === 'completed' && <span className="badge bg-success-soft text-success-text">Done</span>}
                    {item.status === 'error' && (
                      <>
                        <span className="badge bg-danger-soft text-danger-text">Error</span>
                        <button
                          className="text-xs bg-danger-soft hover:bg-danger-border text-danger-text py-0.5 px-2 rounded"
                          onClick={() => handleRetry(item.id)}
                          disabled={(item.retryCount || 0) >= 3}
                        >
                          Retry{(item.retryCount || 0) > 0 ? ` (${item.retryCount})` : ''}
                        </button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}