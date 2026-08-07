# DocuMind AI: Frontend API Contract & SSE Streaming

This document defines the contract for communicating with the DocuMind AI backend for chat and RAG (Retrieval-Augmented Generation) queries. It outlines the request payloads and the Server-Sent Events (SSE) streaming format.

## 1. Request Format

**Endpoint:** `POST /api/chat/stream` (and `POST /api/chat`)
**Content-Type:** `application/json`

Both the streaming and non-streaming endpoints expect the same `ChatRequest` payload.

### Request Body Schema

```typescript
interface ChatRequest {
  // The user's question (required). Min length 1, Max length 2000.
  question: string;
  
  // Optional UUID. If provided, restricts the search to this specific document.
  document_id?: string; 
  
  // Optional UUID. The current conversation context.
  // If omitted, a new conversation is implicitly started (and its ID is returned in metadata).
  conversation_id?: string;
  
  // Number of document chunks to retrieve (default: 5, range: 1-20).
  top_k?: number; 
}
```

## 2. Server-Sent Events (SSE) Streaming Format

**Endpoint:** `POST /api/chat/stream`
**Accept:** `text/event-stream`

The backend streams the response using the SSE protocol. Each chunk is a standard SSE message containing an `event` type and a `data` JSON payload, separated by `\n\n`.

### Event Types

The backend yields the following event types in order:

#### A. `event: metadata`
Sent exactly once, at the very beginning of the stream. It provides the conversation context and citations retrieved before generation begins.

```json
event: metadata
data: {
  "conversation_id": "uuid-string",
  "citations": [
    {
      "chunk_id": "uuid-string",
      "document_id": "uuid-string",
      "filename": "document.pdf",
      "section": "Optional string",
      "page_number": 42,
      "score": 0.85,
      "content_preview": "Snippet of text...",
      "source": "text" // or "ocr"
    }
  ],
  "avg_similarity": 0.85
}
```

#### B. `event: token`
Sent multiple times. Each event contains a piece of the generated answer. The frontend should concatenate `delta` strings to build the full answer in real-time.

```json
event: token
data: {"delta": "The answer is"}

event: token
data: {"delta": " 42."}
```

#### C. `event: done`
Sent exactly once, at the very end of a successful stream. Indicates the backend has finished generation and persisted the messages to the database.

```json
event: done
data: {"latency_ms": 1250}
```

#### D. `event: error`
Sent if an internal error occurs during generation. The stream will terminate immediately after.

```json
event: error
data: {"detail": "An internal error occurred during generation."}
```

## 3. Reference Consumption Snippet (TypeScript)

The following snippet demonstrates how a frontend client (like React) should correctly fetch and parse the SSE stream using the native `fetch` API and `ReadableStream`.

```typescript
export async function sendChatMessageStream(
  request: ChatRequest,
  callbacks: {
    onMetadata?: (data: { conversation_id: string; citations: any[]; avg_similarity: number }) => void;
    onToken?: (delta: string) => void;
    onDone?: (data: { latency_ms: number }) => void;
    onError?: (error: string) => void;
  }
) {
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 'Authorization': `Bearer ${token}` // if applicable
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorMsg = 'Chat request failed';
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch {}
      if (callbacks.onError) callbacks.onError(errorMsg);
      return;
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode the current chunk and append to our buffer
      buffer += decoder.decode(value, { stream: true });
      
      // Split the buffer by double newlines (SSE message separator)
      const blocks = buffer.split('\n\n');
      
      // The last block might be incomplete, keep it in the buffer
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        const lines = block.split('\n');
        let currentEvent = 'message';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            currentData = line.replace('data: ', '').trim();
          }
        }

        if (currentData) {
          try {
            const parsed = JSON.parse(currentData);
            
            if (currentEvent === 'metadata' && callbacks.onMetadata) {
              callbacks.onMetadata(parsed);
            } else if (currentEvent === 'token' && callbacks.onToken) {
              callbacks.onToken(parsed.delta);
            } else if (currentEvent === 'done' && callbacks.onDone) {
              callbacks.onDone(parsed);
            } else if (currentEvent === 'error' && callbacks.onError) {
              callbacks.onError(parsed.detail || 'Stream error');
            }
          } catch (e) {
            console.error('Failed to parse SSE payload:', currentData, e);
          }
        }
      }
    }
  } catch (err) {
    if (callbacks.onError) callbacks.onError((err as Error).message);
  }
}
```
