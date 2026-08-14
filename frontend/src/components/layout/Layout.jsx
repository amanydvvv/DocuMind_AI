import { useState } from 'react';
import DocumentSidebar from '../documents/DocumentSidebar';
import ConversationSidebar from '../sidebar/ConversationSidebar';
import BrandIcon from '../shared/BrandIcon';
import Icon from '../shared/Icon';
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
    <div className="flex h-screen w-screen overflow-hidden bg-background select-none">
      {/* Sidebar Shell */}
      <aside className="w-80 h-full bg-surface border-r border-border flex flex-col overflow-hidden z-20 transition-all duration-200">
        
        {/* Top Branding & Segmented Navigation */}
        <div className="p-4 border-b border-border flex flex-col gap-3.5 bg-surface">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-surface-elevated border border-primary-border flex items-center justify-center shadow-[0_0_14px_rgba(245,158,11,0.25)]">
                <BrandIcon size={18} />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-text text-sm tracking-tight">KueryCore</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full font-semibold bg-primary-soft text-primary-light border border-primary-border">
                    v1.4
                  </span>
                </div>
                <span className="text-[11px] text-text-muted">Enterprise Document AI</span>
              </div>
            </div>
          </div>

          {/* Segmented Switcher */}
          <div 
            className="flex p-1 rounded-xl bg-surface-muted border border-border-subtle" 
            role="tablist" 
            aria-label="Sidebar sections"
          >
            <button
              role="tab"
              aria-selected={activeTab === 'chats'}
              onClick={() => setActiveTab('chats')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-medium tactile-btn cursor-pointer ${
                activeTab === 'chats'
                  ? 'bg-surface-elevated text-text shadow-sm border border-border-strong font-semibold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <span className="text-[11px] text-primary">⬡</span>
              <span>Chats</span>
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'docs'}
              onClick={() => setActiveTab('docs')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-medium tactile-btn cursor-pointer ${
                activeTab === 'docs'
                  ? 'bg-surface-elevated text-text shadow-sm border border-border-strong font-semibold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <span className="text-[11px] text-primary">▣</span>
              <span>Documents</span>
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
          <div className="p-3.5 border-t border-border bg-surface flex items-center justify-between text-xs">
            <div className="flex items-center gap-2.5 min-w-0 pr-2">
              <div className="relative flex-shrink-0">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-primary-dark text-background flex items-center justify-center font-bold text-xs shadow-sm">
                  {user.email ? user.email.charAt(0).toUpperCase() : 'U'}
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-success ring-2 ring-surface"></div>
              </div>
              <div className="min-w-0 flex flex-col">
                <span className="truncate font-medium text-text text-xs">{user.email}</span>
                <span className="text-[10px] text-text-muted flex items-center gap-1">
                  <span className="text-primary text-[9px]">◈</span>
                  <span>Pro Workspace</span>
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="px-2.5 py-1.5 text-text-muted hover:text-danger-text hover:bg-danger-soft border border-transparent hover:border-danger-border rounded-lg text-xs font-medium transition-all tactile-btn cursor-pointer"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        )}
      </aside>

      {/* Main Studio Viewport */}
      <main className="flex-1 h-full overflow-hidden flex flex-col bg-background relative">
        {children}
      </main>
    </div>
  );
}