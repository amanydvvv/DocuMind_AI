import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useConversations } from '../hooks/useConversations';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  fetchConversations: vi.fn().mockResolvedValue([]),
  fetchConversationDetails: vi.fn().mockResolvedValue({ messages: [] }),
  deleteConversation: vi.fn().mockResolvedValue({}),
  authedFetch: vi.fn(),
  friendlyNetworkMessage: vi.fn((err) => err?.message || 'Network error'),
  API_URL: 'http://test',
}));

function streamResponse(...chunks) {
  const queue = chunks.map((c) => new TextEncoder().encode(c));
  let idx = 0;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: async () => {
          if (idx < queue.length) {
            return { done: false, value: queue[idx++] };
          }
          return { done: true };
        },
      }),
    },
  };
}

describe('useConversations State Resiliency', () => {
  it('guarantees isGenerating becomes false on success', async () => {
    api.authedFetch.mockResolvedValue(
      streamResponse('event: metadata\ndata: {"citations":[]}\n\nevent: done\ndata: {}\n\n')
    );

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
  });

  it('guarantees isGenerating becomes false on network error', async () => {
    api.authedFetch.mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
    expect(result.current.error).toBe('Network Error');
  });

  it('guarantees isGenerating becomes false on AbortController timeout', async () => {
    api.authedFetch.mockRejectedValue(new Error('Request timed out'));

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
    expect(result.current.error).toBe('Request timed out');
  });

  it('streams token deltas into the assistant message and stores citations', async () => {
    const citation = { id: 'c1', document_id: 'doc-1', filename: 'report.pdf', page_number: 3 };
    api.authedFetch.mockResolvedValue(
      streamResponse(
        'event: metadata\ndata: ' +
          JSON.stringify({ conversation_id: 'conv-1', citations: [citation], avg_similarity: 0.8 }) +
          '\n\n',
        'event: token\ndata: {"delta":"Hello"}\n\n',
        'event: token\ndata: {"delta":" world"}\n\n',
        'event: done\ndata: {}\n\n'
      )
    );

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hi');
    });

    expect(result.current.activeConversationId).toBe('conv-1');
    expect(result.current.messages).toHaveLength(2);
    const assistant = result.current.messages[1];
    expect(assistant.role).toBe('assistant');
    expect(assistant.content).toBe('Hello world');
    expect(assistant.citations).toHaveLength(1);
    expect(assistant.citations[0].page_number).toBe(3);
    expect(assistant.citations[0].document_id).toBe('doc-1');
    expect(result.current.metadata.citations[0].filename).toBe('report.pdf');
  });
});