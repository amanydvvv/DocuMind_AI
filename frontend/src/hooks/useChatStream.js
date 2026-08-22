import { useCallback, useRef, useState } from 'react';
import { authedFetch, friendlyNetworkMessage, API_URL } from '../services/api';

/**
 * useChatStream — consumption of the backend SSE chat stream.
 *
 * Owns the state of the current chat thread: drives an async `fetch` against
 * /api/chat/stream, decodes the ReadableStream with a TextDecoder, and parses
 * the SSE frames emitted by the backend:
 *   - `event: metadata` -> citations + conversation_id stored in `metadata`
 *   - `event: token`    -> delta appended to the last (assistant) message (typewriter)
 *   - `event: error`    -> bubbled into `error` state for UI toast / banner
 *   - `event: done`     -> stream finished, `isStreaming` flips to false
 */
const STREAM_TIMEOUT_MS = 35000;

export function useChatStream() {
  const [messages, setMessages] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);

  const abortControllerRef = useRef(null);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

  const resetMessages = useCallback((seedMessages = []) => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setMessages(seedMessages);
    setMetadata(null);
    setError(null);
    setIsStreaming(false);
  }, []);

  const appendToLastAssistantMessage = useCallback((updater) => {
    setMessages((prev) => {
      const updated = [...prev];
      const lastIdx = updated.length - 1;
      if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
        updated[lastIdx] = { ...updated[lastIdx], ...updater(updated[lastIdx]) };
      }
      return updated;
    });
  }, []);

  const streamMessage = useCallback(
    async ({
      question,
      document_id = null,
      conversation_id = null,
      top_k = 5,
      onConversationId = null,
      onError = null,
      onDone = null,
    }) => {
      if (!question.trim() || isStreaming) return;

      setError(null);
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const timeoutId = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: '', citations: [] },
      ]);
      setIsStreaming(true);

      try {
        const response = await authedFetch(`${API_URL}/api/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify({ question, document_id, conversation_id, top_k }),
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
          let errorMsg = 'Failed to stream response';
          try {
            const errorData = await response.json();
            errorMsg = errorData.detail || errorMsg;
          } catch {}
          setError(errorMsg);
          if (onError) onError(errorMsg);
          // Failed turn is invisible: drop the question + empty placeholder
          setMessages((prev) => prev.slice(0, -2));
          setIsStreaming(false);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split('\n\n');
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

            if (!currentData) continue;

            let parsed;
            try {
              parsed = JSON.parse(currentData);
            } catch (e) {
              console.error('Failed to parse SSE payload:', currentData, e);
              continue;
            }

            if (currentEvent === 'metadata') {
              setMetadata(parsed);
              if (parsed.conversation_id && parsed.conversation_id !== conversation_id && onConversationId) {
                onConversationId(parsed.conversation_id);
              }
              appendToLastAssistantMessage(() => ({ citations: parsed.citations || [] }));
            } else if (currentEvent === 'token') {
              appendToLastAssistantMessage((last) => ({ content: last.content + parsed.delta }));
            } else if (currentEvent === 'error') {
              const errDetail = parsed.detail || 'Stream error';
              setError(errDetail);
              if (onError) onError(errDetail);
              setMessages((prev) => prev.slice(0, -2));
            } else if (currentEvent === 'done') {
              setIsStreaming(false);
              if (onDone) onDone(parsed);
            }
          }
        }
      } catch (err) {
        console.error('[useChatStream] Chat stream failed:', { url: `${API_URL}/api/chat/stream`, error: err });
        const streamError = friendlyNetworkMessage(err, `${API_URL}/api/chat/stream`);
        setError(streamError);
        if (onError) onError(streamError);
        if (abortControllerRef.current === controller) {
          setMessages((prev) => prev.slice(0, -2));
        }
      } finally {
        clearTimeout(timeoutId);
        setIsStreaming(false);
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }
    },
    [isStreaming, appendToLastAssistantMessage]
  );

  return {
    messages,
    metadata,
    isStreaming,
    error,
    setError,
    abort,
    resetMessages,
    streamMessage,
  };
}