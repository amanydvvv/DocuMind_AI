import React, { useState, useEffect } from 'react';
import Layout from './components/layout/Layout';
import ChatContainer from './components/chat/ChatContainer';
import AuthModal from './components/AuthModal';
import WorkspaceSkeleton from './components/layout/WorkspaceSkeleton';
import { useConversations } from './hooks/useConversations';
import { getAuthToken, removeAuthToken, fetchCurrentUser } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isSigningIn, setIsSigningIn] = useState(false);

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
    setIsSigningIn(true);
    setUser({ id: authData.user_id, email: authData.email });
    if (loadConversationList) await loadConversationList();
    setTimeout(() => {
      setIsSigningIn(false);
    }, 450);
  };

  const handleLogout = () => {
    removeAuthToken();
    setUser(null);
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    if (activeConversation?.title) {
      document.title = `${activeConversation.title} · KueryCore`;
    } else {
      document.title = 'KueryCore';
    }
  }, [activeConversation?.title]);

  if (checkingAuth || isSigningIn) {
    return <WorkspaceSkeleton />;
  }

  if (!user) {
    return (
      <AuthModal
        onAuthSuccess={handleAuthSuccess}
        onStartAuth={() => setIsSigningIn(true)}
      />
    );
  }

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
