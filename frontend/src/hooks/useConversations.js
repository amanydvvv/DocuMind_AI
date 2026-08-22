import { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchConversations,
  fetchConversationDetails,
  deleteConversation,
} from '../services/api';
import { useChatStream } from './useChatStream';

export function useConversations() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const {
    messages,
    metadata,
    isStreaming,
    error,
    setError,
    abort,
    resetMessages,
    streamMessage,
  } = useChatStream();

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
    abort();
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setActiveConversationId(null);
    resetMessages([]);
    setIsLoadingHistory(false);
  }, [abort, resetMessages]);

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

      try {
        const details = await fetchConversationDetails(id, controller.signal);
        resetMessages(details.messages || []);
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
    [activeConversationId, resetMessages, setError]
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
        // Rollback state and surface the error in the banner
        setConversations(previousConversations);
        setError(err.message || 'Conversation not found or could not be deleted.');
      }
    },
    [conversations, activeConversationId, startNewChat, setError]
  );

  const sendMessage = useCallback(
    async (question, documentId = null) => {
      if (!question.trim() || isStreaming) return;

      const isNewChat = !activeConversationId;

      streamMessage({
        question,
        document_id: documentId,
        conversation_id: activeConversationId,
        onConversationId: setActiveConversationId,
        onDone: () => {
          loadConversationList();
          if (isNewChat) {
            setTimeout(loadConversationList, 3000);
            setTimeout(loadConversationList, 6000);
          }
        },
      });
    },
    [activeConversationId, isStreaming, streamMessage, loadConversationList]
  );

  return {
    conversations,
    activeConversationId,
    messages,
    metadata,
    isLoadingHistory,
    isGenerating: isStreaming,
    error,
    clearError: () => setError(null),
    loadConversationList,
    selectConversation,
    startNewChat,
    removeConversation,
    sendMessage,
  };
}