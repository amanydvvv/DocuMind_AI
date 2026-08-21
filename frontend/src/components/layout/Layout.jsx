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

        {/* Top Header Bar — Exactly h-14 to align with ChatContainer header */}
        <div
          className="h-14 px-5 flex items-center justify-between border-b border-white/[0.08] flex-shrink-0"
          style={{
            background: 'linear-gradient(180deg, rgba(13, 29, 21, 0.75) 0%, rgba(9, 20, 16, 0.85) 100%)',
            backdropFilter: 'blur(16px)',
          }}
        >
          <span
            className="font-bold text-[19px] tracking-tight leading-none"
            style={{
              background: 'linear-gradient(135deg, #ffffff 0%, #d1fae5 50%, #00d68f 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            KueryCore
          </span>
        </div>

        {/* Tab Switcher Area */}
        <div className="px-3.5 pt-3 pb-1 flex-shrink-0">
          <div
            className="flex p-1 rounded-xl gap-1"
            style={{
              background: 'rgba(9, 20, 16, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(12px)',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
            }}
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
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-bold transition-all duration-150 cursor-pointer"
                style={
                  activeTab === tab.id
                    ? {
                        background: 'linear-gradient(135deg, rgba(0,214,143,0.22) 0%, rgba(0,214,143,0.08) 100%)',
                        color: '#00ffaa',
                        border: '1px solid rgba(0,214,143,0.38)',
                        boxShadow: '0 2px 10px rgba(0,214,143,0.2), inset 0 1px 0 rgba(255,255,255,0.12)',
                      }
                    : { color: '#94a3b8', border: '1px solid transparent' }
                }
              >
                <span style={activeTab === tab.id ? { color: '#00ffaa', fontSize: '11px' } : { fontSize: '11px', color: '#64748b' }}>
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
                <span className="truncate font-medium text-text text-xs">
                  {user.email?.startsWith('guest_') ? 'Demo Workspace' : user.email}
                </span>
                <span className="text-[10px] text-text-muted flex items-center gap-1">
                  <span style={{ color: '#00d68f', fontSize: '8px' }}>◈</span>
                  {user.email?.startsWith('guest_') ? 'Isolated Session' : 'Pro Workspace'}
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