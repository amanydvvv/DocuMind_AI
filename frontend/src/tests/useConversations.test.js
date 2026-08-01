import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useConversations } from '../hooks/useConversations';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  fetchConversations: vi.fn().mockResolvedValue([]),
  fetchConversationDetails: vi.fn().mockResolvedValue({ messages: [] }),
  deleteConversation: vi.fn().mockResolvedValue({}),
  sendChatMessageStream: vi.fn(),
}));

describe('useConversations State Resiliency', () => {
  it('guarantees isGenerating becomes false on success', async () => {
    api.sendChatMessageStream.mockImplementation(async ({ onDone }) => {
      if (onDone) onDone();
    });

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
  });

  it('guarantees isGenerating becomes false on network error', async () => {
    api.sendChatMessageStream.mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
    expect(result.current.error).toBe('Network Error');
  });

  it('guarantees isGenerating becomes false on AbortController timeout', async () => {
    api.sendChatMessageStream.mockRejectedValue(new Error('Request timed out'));

    const { result } = renderHook(() => useConversations());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.isGenerating).toBe(false);
    expect(result.current.error).toBe('Request timed out');
  });
});
