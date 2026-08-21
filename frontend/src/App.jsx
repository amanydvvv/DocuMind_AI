import React, { useState, useEffect } from 'react';
import Layout from './components/layout/Layout';
import ChatContainer from './components/chat/ChatContainer';
import AuthModal from './components/AuthModal';
import StepForm from './components/shared/StepForm';
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

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    if (activeConversation?.title) {
      document.title = `${activeConversation.title} · KueryCore`;
    } else {
      document.title = 'KueryCore';
    }
  }, [activeConversation?.title]);

  if (checkingAuth) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background text-text font-medium">
        Loading KueryCore AI...
      </div>
    );
  }

  // Preview mode support for testing new components in isolation
  const isStepFormPreview = typeof window !== 'undefined' && window.location.search.includes('preview=stepform');
  if (isStepFormPreview) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background select-none relative overflow-hidden">
        <div className="cosmic-bg" aria-hidden="true">
          <div className="star-layer" />
        </div>
        <div className="z-10 w-full max-w-xl">
          <StepForm onComplete={(data) => alert('Onboarding Completed:\n' + JSON.stringify(data, null, 2))} />
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthModal onAuthSuccess={handleAuthSuccess} />;
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
