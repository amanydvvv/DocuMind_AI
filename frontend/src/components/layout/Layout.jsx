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
      <div className="w-80 h-full bg-surface border-r border-border flex flex-col overflow-hidden">
        {/* Sidebar Header & Tab Switcher */}
        <div className="p-3 border-b border-border bg-surface-muted/40 flex justify-between items-center">
          <span className="font-bold text-text text-base">DocuMind AI</span>
          <div className="flex bg-surface p-0.5 rounded-lg text-xs font-medium" role="tablist" aria-label="Sidebar sections">
            <button
              role="tab"
              aria-selected={activeTab === 'chats'}
              onClick={() => setActiveTab('chats')}
              className={`px-3 py-1 rounded-md transition-all ${
                activeTab === 'chats'
                  ? 'bg-surface-muted text-primary-light shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Chat
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'docs'}
              onClick={() => setActiveTab('docs')}
              className={`px-3 py-1 rounded-md transition-all ${
                activeTab === 'docs'
                  ? 'bg-surface-muted text-primary-light shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Docs
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
          <div className="p-3 border-t border-border bg-surface-muted/40 flex items-center justify-between text-xs text-text-muted">
            <div className="flex items-center space-x-2 truncate">
              <div className="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center font-bold">
                {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
              </div>
              <span className="truncate font-medium text-text-secondary">{user.email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="px-2 py-1 bg-surface-muted hover:bg-danger-soft hover:text-danger-text rounded text-xs transition-colors font-medium"
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