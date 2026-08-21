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
  const [activeTab, setActiveTab] = useState('chats');

  const handleLogout = () => {
    removeAuthToken();
    if (onLogout) onLogout();
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background select-none relative">

      {/* ── Cosmic Starfield Background ── */}
      <div className="cosmic-bg" aria-hidden="true">
        <div className="star-layer" />
      </div>

      {/* ── Sidebar ── */}
      <aside
        className="w-72 h-full flex flex-col overflow-hidden z-20 relative"
        style={{
          background: 'linear-gradient(180deg, rgba(9,20,16,0.98) 0%, rgba(5,13,8,0.98) 100%)',
          borderRight: '1px solid rgba(0,214,143,0.08)',
          boxShadow: '4px 0 40px rgba(0,0,0,0.7)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Top green hairline */}
        <div
          className="absolute top-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(0,214,143,0.5), transparent)' }}
        />

        {/* Branding */}
        <div className="p-4 pb-3 flex flex-col gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex flex-col min-w-0">
              <span
                className="font-bold text-[15px] tracking-tight"
                style={{
                  background: 'linear-gradient(135deg, #e8f5ee 0%, #00d68f 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                KueryCore
              </span>
            </div>
          </div>

          {/* Segmented Switcher */}
          <div
            className="flex p-0.5 rounded-lg gap-0.5"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,214,143,0.07)' }}
            role="tablist"
          >
            {[
              { id: 'chats', label: 'Chats', icon: '⬡' },
              { id: 'docs', label: 'Documents', icon: '▣' },
            ].map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer"
                style={
                  activeTab === tab.id
                    ? {
                        background: 'linear-gradient(135deg, rgba(0,214,143,0.16) 0%, rgba(0,214,143,0.06) 100%)',
                        color: '#00d68f',
                        border: '1px solid rgba(0,214,143,0.22)',
                        boxShadow: '0 1px 8px rgba(0,214,143,0.1)',
                      }
                    : { color: 'var(--color-text-muted)', border: '1px solid transparent' }
                }
              >
                <span style={activeTab === tab.id ? { color: '#00d68f', fontSize: '10px' } : { fontSize: '10px' }}>
                  {tab.icon}
                </span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
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

        {/* User Footer */}
        {user && (
          <div
            className="p-3 flex items-center justify-between gap-2"
            style={{
              borderTop: '1px solid rgba(0,214,143,0.06)',
              background: 'rgba(0,214,143,0.02)',
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className="relative flex-shrink-0">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs"
                  style={{
                    background: 'linear-gradient(135deg, #00d68f, #00a86b)',
                    color: '#050d08',
                    boxShadow: '0 0 12px rgba(0,214,143,0.35)',
                  }}
                >
                  {user.email?.charAt(0).toUpperCase() ?? 'U'}
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-[#050d08]" />
              </div>
              <div className="min-w-0 flex flex-col">
                <span className="truncate font-medium text-text text-xs">{user.email}</span>
                <span className="text-[10px] text-text-muted flex items-center gap-1">
                  <span style={{ color: '#00d68f', fontSize: '8px' }}>◈</span>
                  Pro Workspace
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="px-2 py-1 text-text-muted hover:text-red-400 rounded-lg text-xs font-medium transition-all cursor-pointer flex-shrink-0"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.05)' }}
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        )}

        {/* Bottom green hairline */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(0,214,143,0.12), transparent)' }}
        />
      </aside>

      {/* ── Main Viewport ── */}
      <main className="flex-1 h-full overflow-hidden flex flex-col relative z-10">
        {children}
      </main>
    </div>
  );
}