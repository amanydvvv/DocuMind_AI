import { useState, useRef, useReducer, useEffect } from 'react';
import { uploadDocument, getDocument } from '../../services/api';
import Icon from '../shared/Icon';

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

  const completedCount = fileQueue.filter(i => i.status === 'completed' || i.status === 'error').length;
  const progressPercent = fileQueue.length > 0 ? (completedCount / fileQueue.length) * 100 : 0;

  return (
    <div className="flex flex-col gap-3">
      {/* Tactile Clay Drop Zone */}
      <div
        className={`relative border-2 border-dashed rounded-2xl p-5 text-center transition-all duration-200 cursor-pointer ${
          isDragging 
            ? 'border-primary bg-primary-soft shadow-[0_0_24px_rgba(245,158,11,0.25)]' 
            : 'border-border bg-surface hover:border-primary-border hover:bg-surface-elevated'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf,.md,.txt"
          multiple
        />
        <div className="flex flex-col items-center justify-center pointer-events-none">
          <div className="w-9 h-9 rounded-xl bg-surface-muted border border-primary-border flex items-center justify-center text-primary mb-2.5 shadow-sm text-sm font-bold">
            ◈
          </div>
          <p className="text-xs font-semibold text-text">Drag &amp; drop files here</p>
          <p className="text-[11px] text-text-muted mt-0.5">or click to browse (.pdf, .md, .txt)</p>
        </div>
      </div>

      {/* Queue Progress & List */}
      {fileQueue.length > 0 && (
        <div className="p-3 rounded-xl bg-surface border border-border flex flex-col gap-2.5 shadow-sm">
          {/* Overall Progress Bar */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-semibold text-text-secondary flex items-center gap-1">
                <span className="text-primary text-[9px]">▣</span>
                <span>Queue: {completedCount}/{fileQueue.length} files</span>
              </span>
              <button
                className="text-[10px] text-text-muted hover:text-text px-2 py-0.5 rounded-md hover:bg-surface-muted transition-colors cursor-pointer"
                onClick={handleClearFinished}
              >
                Clear Finished
              </button>
            </div>
            <div className="w-full bg-surface-muted h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-primary to-primary-hover h-full transition-all duration-300 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Queue Items */}
          <ul className="space-y-1.5 max-h-48 overflow-y-auto">
            {fileQueue.map(item => (
              <li 
                key={item.id} 
                className="flex items-center justify-between p-2 rounded-lg bg-surface-muted border border-border-subtle text-xs"
              >
                <div className="flex-1 min-w-0 pr-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-primary text-[10px]">◇</span>
                    <span className="font-medium text-text truncate" title={item.name}>
                      {item.name}
                    </span>
                    <span className="text-[10px] text-text-muted flex-shrink-0">
                      ({(item.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  {item.errorMessage && (
                    <p className="text-[10px] text-danger-text truncate mt-0.5">
                      {item.errorMessage}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {item.status === 'queued' && (
                    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-surface text-text-muted border border-border-subtle">
                      Queued
                    </span>
                  )}
                  {item.status === 'uploading' && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-primary-soft text-primary-light border border-primary-border">
                      <span className="w-1 h-1 rounded-full bg-primary animate-ping"></span>
                      Uploading
                    </span>
                  )}
                  {item.status === 'processing' && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-warning-soft text-warning-text border border-warning-border">
                      <span className="w-1 h-1 rounded-full bg-warning animate-pulse"></span>
                      Embedding
                    </span>
                  )}
                  {item.status === 'completed' && (
                    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-success-soft text-success-text border border-success-border">
                      Done
                    </span>
                  )}
                  {item.status === 'error' && (
                    <div className="flex items-center gap-1">
                      <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-danger-soft text-danger-text border border-danger-border">
                        Error
                      </span>
                      <button
                        className="text-[10px] bg-danger-soft hover:bg-danger-border text-danger-text px-1.5 py-0.5 rounded transition-colors cursor-pointer"
                        onClick={() => handleRetry(item.id)}
                        disabled={(item.retryCount || 0) >= 3}
                      >
                        Retry{(item.retryCount || 0) > 0 ? ` (${item.retryCount})` : ''}
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}