const DEFAULT_API_URL = 'https://documind-ai-97t5.onrender.com';
const API_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/+$/, '');

function redactHeaders(headers) {
  const out = {};
  for (const [key, value] of Object.entries(headers || {})) {
    if (/authorization/i.test(key)) {
      out[key] = `Bearer <redacted:${String(value).length} chars>`;
    } else {
      out[key] = value;
    }
  }
  return out;
}

export function friendlyNetworkMessage(err, url) {
  const isNetworkFailure =
    err instanceof TypeError ||
    /failed to fetch|fetch failed|networkerror|load failed/i.test(String((err && err.message) || err));
  if (isNetworkFailure) {
    return (
      `Could not reach the server at ${url || API_URL}. ` +
      `If the backend is waking up from a free-tier cold start, it can take up to a minute ` +
      `— please wait a moment and try again.`
    );
  }
  return (err && err.message) || 'Unexpected network error';
}

async function fetchWithDiagnostics(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = redactHeaders(options.headers || {});
  const signalInfo = options.signal ? { aborted: options.signal.aborted } : undefined;

  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      console.error(
        `[API] Non-OK response for ${method} ${url}`,
        { status: response.status, statusText: response.statusText, headers, signalInfo }
      );
    }
    return response;
  } catch (err) {
    console.error(
      `[API] Network request failed for ${method} ${url}`,
      { headers, signalInfo, error: err }
    );
    throw err;
  }
}

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
  localStorage.removeItem('documind_refresh_token');
}

export function setAuthData(data) {
  if (data.access_token) setAuthToken(data.access_token);
  if (data.refresh_token) {
    localStorage.setItem('documind_refresh_token', data.refresh_token);
  } else {
    localStorage.removeItem('documind_refresh_token');
  }
}

export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('documind_refresh_token');
  if (!refreshToken) throw new Error('No refresh token');

  let response;
  try {
    response = await fetchWithDiagnostics(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (err) {
    throw new Error(friendlyNetworkMessage(err, `${API_URL}/api/auth/refresh`));
  }

  if (!response.ok) {
    removeAuthToken();
    throw new Error('Session expired. Please log in again.');
  }

  const data = await response.json();
  setAuthData(data);
  return data.access_token;
}

async function authedFetch(url, options = {}, retry = true) {
  const headers = { ...(options.headers || {}) };
  const token = getAuthToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let response;
  try {
    response = await fetchWithDiagnostics(url, { ...options, headers });
  } catch (err) {
    throw new Error(friendlyNetworkMessage(err, url));
  }

  if (response.status === 401 && retry) {
    try {
      const newToken = await refreshAccessToken();
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetchWithDiagnostics(url, { ...options, headers });
    } catch (e) {
      window.dispatchEvent(new CustomEvent('auth-expired'));
      throw e;
    }
  }

  return response;
}

export async function loginUser(email, password) {
  let response;
  try {
    response = await fetchWithDiagnostics(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    throw new Error(friendlyNetworkMessage(err, `${API_URL}/api/auth/login`));
  }

  if (!response.ok) {
    let errorMsg = 'Login failed';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  const data = await response.json();
  setAuthData(data);
  return data;
}

export async function signupUser(email, password) {
  let response;
  try {
    response = await fetchWithDiagnostics(`${API_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    throw new Error(friendlyNetworkMessage(err, `${API_URL}/api/auth/signup`));
  }

  if (!response.ok) {
    let errorMsg = 'Signup failed';
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  const data = await response.json();
  setAuthData(data);
  return data;
}

export async function fetchCurrentUser() {
  const response = await authedFetch(`${API_URL}/api/auth/me`);
  if (!response.ok) {
    removeAuthToken();
    throw new Error('Unauthorized');
  }
  return response.json();
}

export async function fetchDocuments() {
  const response = await authedFetch(`${API_URL}/api/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

export async function getDocument(documentId) {
  const response = await authedFetch(`${API_URL}/api/documents/${documentId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch document status');
  }
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await authedFetch(`${API_URL}/api/documents/upload`, {
    method: 'POST',
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
  const response = await authedFetch(`${API_URL}/api/documents/${documentId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to delete document');
  }
}

export async function sendChatMessage({ question, document_id = null, conversation_id = null, top_k = 5 }) {
  const response = await authedFetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const response = await authedFetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        question,
        document_id,
        conversation_id,
        top_k,
      }),
    });
    clearTimeout(timeoutId);

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
    console.error('[API] Chat stream failed:', { url: `${API_URL}/api/chat/stream`, error: err });
    if (onError) onError(friendlyNetworkMessage(err, `${API_URL}/api/chat/stream`));
  }
}

export async function fetchConversations() {
  const response = await authedFetch(`${API_URL}/api/conversations`);
  if (!response.ok) {
    throw new Error('Failed to fetch conversation sessions');
  }
  const data = await response.json();
  return data.conversations || [];
}

export async function fetchConversationDetails(conversationId, signal = null) {
  const response = await authedFetch(`${API_URL}/api/conversations/${conversationId}`, {
    signal,
  });
  if (!response.ok) {
    throw new Error('Failed to fetch conversation history');
  }
  return response.json();
}

export async function deleteConversation(conversationId) {
  const response = await authedFetch(`${API_URL}/api/conversations/${conversationId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to delete conversation');
  }
}
