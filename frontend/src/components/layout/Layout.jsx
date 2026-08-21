import { useState } from 'react';
import DocumentSidebar from '../documents/DocumentSidebar';
import ConversationSidebar from '../sidebar/ConversationSidebar';
import BrandIcon from '../shared/BrandIcon';
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
    <div className="flex h-screen w-screen overflow-hidden bg-background select-none">

      {/* ── Sidebar ── */}
      <aside
        className="w-72 h-full flex flex-col overflow-hidden z-20 relative"
        style={{
          background: 'linear-gradient(180deg, #0f1118 0%, #0a0b10 100%)',
          borderRight: '1px solid rgba(245,158,11,0.08)',
          boxShadow: '4px 0 40px rgba(0,0,0,0.6)',
        }}
      >
        {/* Top amber hairline */}
        <div
          className="absolute top-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(245,158,11,0.5), transparent)' }}
        />

        {/* Branding */}
        <div className="p-4 pb-3 flex flex-col gap-3">
          <div className="flex items-center gap-2.5">
            {/* Logo */}
            <div
              className="relative w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, #1c1a0e 0%, #2a1f00 100%)',
                border: '1px solid rgba(245,158,11,0.35)',
                boxShadow: '0 0 18px rgba(245,158,11,0.22), inset 0 1px 0 rgba(255,255,255,0.06)',
              }}
            >
              <BrandIcon size={17} />
              <div
                className="absolute inset-0 rounded-xl animate-pulse pointer-events-none"
                style={{ background: 'radial-gradient(circle at 50% 0%, rgba(245,158,11,0.18), transparent 70%)' }}
              />
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5">
                <span
                  className="font-bold text-sm tracking-tight"
                  style={{
                    background: 'linear-gradient(135deg, #f1f5f9 0%, #fde68a 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  KueryCore
                </span>
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded-full font-bold tracking-wide"
                  style={{ background: 'rgba(245,158,11,0.15)', color: '#fde68a', border: '1px solid rgba(245,158,11,0.25)' }}
                >
                  v1.4
                </span>
              </div>
              <span className="text-[10px] text-text-muted truncate">Enterprise Document AI</span>
            </div>
          </div>

          {/* Segmented Switcher */}
          <div
            className="flex p-0.5 rounded-lg gap-0.5"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
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
                        background: 'linear-gradient(135deg, rgba(245,158,11,0.18) 0%, rgba(245,158,11,0.07) 100%)',
                        color: '#fde68a',
                        border: '1px solid rgba(245,158,11,0.22)',
                        boxShadow: '0 1px 8px rgba(245,158,11,0.12)',
                      }
                    : { color: 'var(--color-text-muted)', border: '1px solid transparent' }
                }
              >
                <span style={activeTab === tab.id ? { color: '#f59e0b', fontSize: '10px' } : { fontSize: '10px' }}>
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
              borderTop: '1px solid rgba(255,255,255,0.05)',
              background: 'rgba(255,255,255,0.015)',
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className="relative flex-shrink-0">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs"
                  style={{
                    background: 'linear-gradient(135deg, #f59e0b, #b45309)',
                    color: '#09090b',
                    boxShadow: '0 0 12px rgba(245,158,11,0.35)',
                  }}
                >
                  {user.email?.charAt(0).toUpperCase() ?? 'U'}
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-[#0a0b10]" />
              </div>
              <div className="min-w-0 flex flex-col">
                <span className="truncate font-medium text-text text-xs">{user.email}</span>
                <span className="text-[10px] text-text-muted flex items-center gap-1">
                  <span style={{ color: '#f59e0b', fontSize: '8px' }}>◈</span>
                  Pro Workspace
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="px-2 py-1 text-text-muted hover:text-red-400 rounded-lg text-xs font-medium transition-all cursor-pointer flex-shrink-0"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        )}

        {/* Bottom amber hairline */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(245,158,11,0.12), transparent)' }}
        />
      </aside>

      {/* ── Main Viewport ── */}
      <main className="flex-1 h-full overflow-hidden flex flex-col bg-background relative">
        {/* Subtle dot-grid texture */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        {children}
      </main>
    </div>
  );
}