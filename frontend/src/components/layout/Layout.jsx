import { useState } from 'react';
import DocumentSidebar from '../documents/DocumentSidebar';
import ConversationSidebar from '../sidebar/ConversationSidebar';
import { removeAuthToken } from '../../services/api';

export default function Layout({
  user,
  onLogout,
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNewChat,
  onDeleteConversation,
  children,
}) {
  const [activeTab, setActiveTab] = useState('chats'); // 'chats' | 'docs'

  const handleLogout = () => {
    removeAuthToken();
    if (onLogout) onLogout();
  };

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

        {/* User Profile & Logout Footer */}
        {user && (
          <div className="p-3 border-t border-border bg-gray-50 flex items-center justify-between text-xs text-text-muted">
            <div className="flex items-center space-x-2 truncate">
              <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold">
                {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
              </div>
              <span className="truncate font-medium text-gray-700">{user.email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="px-2 py-1 bg-gray-200 hover:bg-red-100 hover:text-red-600 rounded text-xs transition-colors font-medium"
            >
              Logout
            </button>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  );
}
