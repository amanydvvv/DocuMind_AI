import { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchConversations,
  fetchConversationDetails,
  deleteConversation,
  sendChatMessageStream,
} from '../services/api';

export function useConversations() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const abortControllerRef = useRef(null);

  const loadConversationList = useCallback(async () => {
    try {
      const list = await fetchConversations();
      setConversations(list);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, []);

  useEffect(() => {
    loadConversationList();
  }, [loadConversationList]);

  const startNewChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setActiveConversationId(null);
    setMessages([]);
    setIsLoadingHistory(false);
    setError(null);
  }, []);

  const selectConversation = useCallback(
    async (id) => {
      if (!id || id === activeConversationId) return;

      // Prevent race conditions by aborting any in-flight thread fetch
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setActiveConversationId(id);
      setIsLoadingHistory(true);
      setError(null);

      try {
        const details = await fetchConversationDetails(id, controller.signal);
        setMessages(details.messages || []);
      } catch (err) {
        if (err.name === 'AbortError') return;
        setError(err.message || 'Failed to load thread messages');
        console.error('Error loading conversation details:', err);
      } finally {
        if (abortControllerRef.current === controller) {
          setIsLoadingHistory(false);
        }
      }
    },
    [activeConversationId]
  );

  const removeConversation = useCallback(
    async (id) => {
      const previousConversations = [...conversations];
      // Optimistic removal
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeConversationId) {
        startNewChat();
      }
      try {
        await deleteConversation(id);
      } catch (err) {
        // Rollback state on error
        setConversations(previousConversations);
        setError(err.message || 'Conversation not found or could not be deleted.');
      }
    },
    [conversations, activeConversationId, startNewChat]
  );

  const sendMessage = useCallback(
    async (question, documentId = null) => {
      if (!question.trim() || isGenerating) return;

      setError(null);
      const userMsg = { role: 'user', content: question };
      setMessages((prev) => [...prev, userMsg]);
      setIsGenerating(true);

      let assistantCreated = false;

      try {
        await sendChatMessageStream({
          question,
          document_id: documentId,
          conversation_id: activeConversationId,
          onMetadata: (metadata) => {
            if (metadata.conversation_id && metadata.conversation_id !== activeConversationId) {
              setActiveConversationId(metadata.conversation_id);
            }
            if (!assistantCreated) {
              assistantCreated = true;
              setMessages((prev) => [
                ...prev,
                {
                  role: 'assistant',
                  content: '',
                  citations: metadata.citations || [],
                },
              ]);
            }
          },
          onToken: (tokenDelta) => {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: updated[lastIdx].content + tokenDelta,
                };
              }
              return updated;
            });
          },
          onError: (errDetail) => {
            setError(errDetail || 'Failed to generate response');
            if (!assistantCreated) {
              setMessages((prev) => prev.slice(0, -1));
            }
          },
          onDone: () => {
            loadConversationList();
          },
        });
      } catch (err) {
        setError(err.message || 'Error sending message');
      } finally {
        setIsGenerating(false);
      }
    },
    [activeConversationId, isGenerating, loadConversationList]
  );

  return {
    conversations,
    activeConversationId,
    messages,
    isLoadingHistory,
    isGenerating,
    error,
    loadConversationList,
    selectConversation,
    startNewChat,
    removeConversation,
    sendMessage,
  };
}
