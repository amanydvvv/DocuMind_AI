import React, { useState, useEffect } from 'react';
import Layout from './components/layout/Layout';
import ChatContainer from './components/chat/ChatContainer';
import AuthModal from './components/AuthModal';
import { useConversations } from './hooks/useConversations';
import { getAuthToken, removeAuthToken, fetchCurrentUser } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  const {
    conversations,
    activeConversationId,
    messages,
    isLoadingHistory,
    isGenerating,
    error,
    clearError,
    selectConversation,
    startNewChat,
    removeConversation,
    sendMessage,
    loadConversationList,
  } = useConversations();

  useEffect(() => {
    async function initAuth() {
      const token = getAuthToken();
      if (!token) {
        setCheckingAuth(false);
        return;
      }
      try {
        const u = await fetchCurrentUser();
        setUser(u);
        if (loadConversationList) loadConversationList();
      } catch (err) {
        setUser(null);
      } finally {
        setCheckingAuth(false);
      }
    }
    initAuth();

    const handleAuthExpired = () => setUser(null);
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  const handleAuthSuccess = async (authData) => {
    setUser({ id: authData.user_id, email: authData.email });
    if (loadConversationList) loadConversationList();
  };

  const handleLogout = () => {
    removeAuthToken();
    setUser(null);
  };

  if (checkingAuth) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-white font-medium">
        Loading DocuMind AI...
      </div>
    );
  }

  if (!user) {
    return <AuthModal onAuthSuccess={handleAuthSuccess} />;
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  return (
    <Layout
      user={user}
      onLogout={handleLogout}
      conversations={conversations}
      activeConversationId={activeConversationId}
      onSelectConversation={selectConversation}
      onStartNewChat={startNewChat}
      onDeleteConversation={removeConversation}
    >
      <ChatContainer
        activeConversation={activeConversation}
        messages={messages}
        isLoadingHistory={isLoadingHistory}
        isGenerating={isGenerating}
        error={error}
        onDismissError={clearError}
        onSendMessage={sendMessage}
      />
    </Layout>
  );
}

export default App;
