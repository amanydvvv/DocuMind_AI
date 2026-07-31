import { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchConversations,
  fetchConversationDetails,
  deleteConversation,
  sendChatMessage,
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
      try {
        await deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (id === activeConversationId) {
          startNewChat();
        }
      } catch (err) {
        alert('Failed to delete conversation: ' + err.message);
      }
    },
    [activeConversationId, startNewChat]
  );

  const sendMessage = useCallback(
    async (question, documentId = null) => {
      if (!question.trim() || isGenerating) return;

      setError(null);
      const userMsg = { role: 'user', content: question };
      setMessages((prev) => [...prev, userMsg]);
      setIsGenerating(true);

      try {
        const response = await sendChatMessage({
          question,
          document_id: documentId,
          conversation_id: activeConversationId,
        });

        const assistantMsg = {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
        };

        setMessages((prev) => [...prev, assistantMsg]);

        if (response.conversation_id && response.conversation_id !== activeConversationId) {
          setActiveConversationId(response.conversation_id);
        }

        // Silently refresh conversation list to show new title/timestamp
        loadConversationList();
      } catch (err) {
        setError(err.message || 'Failed to send message');
        // Rollback optimistic user message
        setMessages((prev) => prev.slice(0, -1));
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
