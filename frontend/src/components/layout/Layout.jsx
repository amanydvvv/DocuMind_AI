import { useState } from 'react';
import DocumentSidebar from '../documents/DocumentSidebar';
import ConversationSidebar from '../sidebar/ConversationSidebar';

export default function Layout({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
  children,
}) {
  const [activeTab, setActiveTab] = useState('chats'); // 'chats' | 'docs'

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Sidebar Shell */}
      <div className="w-80 h-full bg-white border-r border-border flex flex-col overflow-hidden">
        {/* Sidebar Header & Tab Switcher */}
        <div className="p-3 border-b border-border bg-gray-50/50 flex justify-between items-center">
          <span className="font-bold text-text text-base">DocuMind AI</span>
          <div className="flex bg-gray-200/80 p-0.5 rounded-lg text-xs font-medium">
            <button
              onClick={() => setActiveTab('chats')}
              className={`px-3 py-1 rounded-md transition-all ${
                activeTab === 'chats'
                  ? 'bg-white text-primary shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              💬 Chats
            </button>
            <button
              onClick={() => setActiveTab('docs')}
              className={`px-3 py-1 rounded-md transition-all ${
                activeTab === 'docs'
                  ? 'bg-white text-primary shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              📄 Docs
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeTab === 'chats' ? (
            <ConversationSidebar
              conversations={conversations}
              activeConversationId={activeConversationId}
              onSelectConversation={onSelectConversation}
              onStartNewChat={onStartNewChat}
              onDeleteConversation={onDeleteConversation}
            />
          ) : (
            <DocumentSidebar />
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  );
}
