const API_URL = import.meta.env.VITE_API_URL || 'https://documind-ai-97t5.onrender.com';

export function getAuthToken() {
  return localStorage.getItem('documind_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('documind_token', token);
  } else {
    localStorage.removeItem('documind_token');
  }
}

export function removeAuthToken() {
  localStorage.removeItem('documind_token');
}

function getAuthHeaders(customHeaders = {}) {
  const token = getAuthToken();
  const headers = { ...customHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(email, password) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let errorMsg = 'Login failed';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

export async function signupUser(email, password) {
  const response = await fetch(`${API_URL}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let errorMsg = 'Signup failed';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

export async function fetchCurrentUser() {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    removeAuthToken();
    throw new Error('Unauthorized');
  }
  return response.json();
}

export async function fetchDocuments() {
  const response = await fetch(`${API_URL}/api/documents`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

export async function getDocument(documentId) {
  const response = await fetch(`${API_URL}/api/documents/${documentId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch document status');
  }
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/api/documents/upload`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    let errorMsg = 'Upload failed';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_URL}/api/documents/${documentId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to delete document');
  }
}

export async function sendChatMessage({ question, document_id = null, conversation_id = null, top_k = 5 }) {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      question,
      document_id,
      conversation_id,
      top_k,
    }),
  });

  if (!response.ok) {
    let errorMsg = 'Failed to send message';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function sendChatMessageStream({
  question,
  document_id = null,
  conversation_id = null,
  top_k = 5,
  onMetadata,
  onToken,
  onError,
  onDone,
}) {
  try {
    const response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        question,
        document_id,
        conversation_id,
        top_k,
      }),
    });

    if (!response.ok) {
      let errorMsg = 'Failed to stream response';
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (e) {}
      if (onError) onError(errorMsg);
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

        if (currentData) {
          try {
            const parsed = JSON.parse(currentData);
            if (currentEvent === 'metadata' && onMetadata) {
              onMetadata(parsed);
            } else if (currentEvent === 'token' && onToken) {
              onToken(parsed.delta);
            } else if (currentEvent === 'done' && onDone) {
              onDone(parsed);
            } else if (currentEvent === 'error' && onError) {
              onError(parsed.detail || 'Stream error');
            }
          } catch (e) {
            console.error('Failed to parse SSE payload:', currentData, e);
          }
        }
      }
    }
  } catch (err) {
    if (onError) onError(err.message || 'Network streaming failure');
  }
}

export async function fetchConversations() {
  const response = await fetch(`${API_URL}/api/conversations`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch conversation sessions');
  }
  const data = await response.json();
  return data.conversations || [];
}

export async function fetchConversationDetails(conversationId, signal = null) {
  const response = await fetch(`${API_URL}/api/conversations/${conversationId}`, {
    signal,
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch conversation history');
  }
  return response.json();
}

export async function deleteConversation(conversationId) {
  const response = await fetch(`${API_URL}/api/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to delete conversation');
  }
}
