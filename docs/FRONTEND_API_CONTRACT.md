# KueryCore AI: Frontend API Contract

This document outlines the exact request and response schemas for the RAG Chat API endpoints, ensuring synchronization between the frontend consumption and backend emission of data.

## 1. Standard Chat Endpoint

**Endpoint:** `POST /api/chat`
**Content-Type:** `application/json`

This endpoint returns a complete, non-streaming response.

### Request Body Schema
```json
{
  "question": "string (min: 1, max: 2000)",
  "document_id": "uuid (optional) - Scope search to a specific document",
  "conversation_id": "uuid (optional) - Continue an existing conversation",
  "top_k": "integer (optional, default: 5, min: 1, max: 20) - Number of chunks to retrieve"
}
```

### Response Body Schema
```json
{
  "answer": "string",
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "filename": "string",
      "section": "string (optional)",
      "page_number": "integer (optional)",
      "score": "float",
      "content_preview": "string",
      "source": "string (optional, e.g., 'text', 'ocr')"
    }
  ],
  "conversation_id": "uuid",
  "latency_ms": "integer",
  "avg_similarity": "float"
}
```

---

## 2. Streaming Chat Endpoint (Server-Sent Events)

**Endpoint:** `POST /api/chat/stream`
**Content-Type:** `application/json`
**Response-Type:** `text/event-stream`

This endpoint streams the LLM response chunk by chunk using Server-Sent Events (SSE).

### Request Body Schema
Same as `/api/chat`.
```json
{
  "question": "string (min: 1, max: 2000)",
  "document_id": "uuid (optional)",
  "conversation_id": "uuid (optional)",
  "top_k": "integer (optional, default: 5)"
}
```

### SSE Event Schemas

The streaming response yields discrete events separated by `\n\n`. Each event has an `event` type and a JSON `data` payload.

#### A. Metadata Event (`event: metadata`)
Emitted exactly **once** at the start of the stream. Contains the conversation ID and citations found.
```text
event: metadata
data: {"conversation_id": "uuid", "citations": [{"chunk_id": "uuid", "document_id": "uuid", "filename": "string", "display_title": "string (optional, may equal filename)", "page_number": 1, "score": 0.85, "content_preview": "...", "source": "text"}], "avg_similarity": 0.85}
```

#### B. Token Event (`event: token`)
Emitted **multiple times** as the LLM generates tokens.
```text
event: token
data: {"delta": "Hello"}
```
*(The frontend should concatenate all `delta` values to form the complete answer.)*

#### C. Done Event (`event: done`)
Emitted exactly **once** when the generation successfully finishes.
```text
event: done
data: {"latency_ms": 1250}
```

#### D. Error Event (`event: error`)
Emitted if an exception occurs during generation. The stream will close immediately after.
```text
event: error
data: {"detail": "An internal error occurred during generation."}
```

### Frontend Consumption Example (TypeScript)

The frontend must manually handle the `fetch` request and parse the SSE stream (e.g., using `@microsoft/fetch-event-source` or manual reader).

```typescript
async function fetchChatStream(question: string) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}` // If applicable
    },
    body: JSON.stringify({ question })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader!.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    
    // Process full SSE messages separated by \n\n
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || ''; // keep incomplete chunk in buffer
    
    for (const part of parts) {
      if (!part.trim()) continue;
      
      const lines = part.split('\n');
      let eventType = 'message';
      let data = '';
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.replace('event: ', '').trim();
        } else if (line.startsWith('data: ')) {
          data = line.replace('data: ', '').trim();
        }
      }
      
      const parsedData = JSON.parse(data);
      
      switch (eventType) {
        case 'metadata':
          console.log('Got citations:', parsedData.citations);
          console.log('Conversation ID:', parsedData.conversation_id);
          break;
        case 'token':
          process.stdout.write(parsedData.delta); // append token to UI
          break;
        case 'done':
          console.log('\nFinished in ms:', parsedData.latency_ms);
          break;
        case 'error':
          console.error('Stream error:', parsedData.detail);
          break;
      }
    }
  }
}
```
