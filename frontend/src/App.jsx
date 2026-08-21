import React, { useState, useEffect } from 'react';
import Layout from './components/layout/Layout';
import ChatContainer from './components/chat/ChatContainer';
import AuthModal from './components/AuthModal';
import ResetPassword from './components/ResetPassword';
import WorkspaceSkeleton from './components/layout/WorkspaceSkeleton';
import { useConversations } from './hooks/useConversations';
import { getAuthToken, removeAuthToken, fetchCurrentUser } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isSigningIn, setIsSigningIn] = useState(false);

  // Detect /reset-password route without a full router dependency
  const isResetRoute = window.location.pathname === '/reset-password';

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
    // Skip auth check on the reset-password route — no token needed there
    if (isResetRoute) {
      setCheckingAuth(false);
      return;
    }

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
    // Only show the skeleton AFTER confirmed auth success — never before.
    setIsSigningIn(true);
    setUser({ id: authData.user_id, email: authData.email });
    try {
      if (loadConversationList) await loadConversationList();
    } catch {
      // Non-critical: workspace still loads without conversation list
    }
    setTimeout(() => {
      setIsSigningIn(false);
    }, 450);
  };

  // Called by AuthModal when auth fails — ensures skeleton never stays stuck
  const handleAuthError = () => {
    setIsSigningIn(false);
  };

  const handleLogout = () => {
    removeAuthToken();
    setUser(null);
  };

  // Navigate back to sign-in from the reset-password page
  const handleNavigateToSignIn = () => {
    window.history.replaceState(null, '', '/');
    window.location.reload(); // simplest SPA re-entry without a full router
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    if (activeConversation?.title) {
      document.title = `${activeConversation.title} · KueryCore`;
    } else {
      document.title = 'KueryCore';
    }
  }, [activeConversation?.title]);

  // ── Reset password route ──────────────────────────────
  if (isResetRoute) {
    return <ResetPassword onNavigateToSignIn={handleNavigateToSignIn} />;
  }

  // ── Loading / skeleton ────────────────────────────────
  if (checkingAuth || isSigningIn) {
    return <WorkspaceSkeleton />;
  }

  // ── Auth gate ─────────────────────────────────────────
  if (!user) {
    return (
      <AuthModal
        onAuthSuccess={handleAuthSuccess}
        onAuthError={handleAuthError}
      />
    );
  }

  // ── Workspace ─────────────────────────────────────────
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
