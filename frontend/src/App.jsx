import Layout from './components/layout/Layout';
import ChatContainer from './components/chat/ChatContainer';
import { useConversations } from './hooks/useConversations';

function App() {
  const {
    conversations,
    activeConversationId,
    messages,
    isLoadingHistory,
    isGenerating,
    error,
    selectConversation,
    startNewChat,
    removeConversation,
    sendMessage,
  } = useConversations();

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  return (
    <Layout
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
        onSendMessage={sendMessage}
      />
    </Layout>
  );
}

export default App;
