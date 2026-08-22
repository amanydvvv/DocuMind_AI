import React from 'react';

/**
 * WorkspaceSkeleton — Full Screen Shimmer Skeleton Workspace Transition
 * Displayed seamlessly after sign-in / demo initialization while loading workspace data.
 */
export default function WorkspaceSkeleton({ onDismiss }) {
  const [showSlowWarning, setShowSlowWarning] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => setShowSlowWarning(true), 2500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex h-screen w-screen bg-[#050d08] text-white overflow-hidden select-none animate-in fade-in duration-200 relative">
      {/* ── Slow Connection / Cold-start Notification ── */}
      {showSlowWarning && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div
            className="flex items-center gap-3 px-4 py-2 rounded-full text-xs"
            style={{
              background: 'rgba(13, 29, 21, 0.95)',
              border: '1px solid rgba(0, 214, 143, 0.3)',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 214, 143, 0.15)',
              backdropFilter: 'blur(16px)',
            }}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-slate-300">Connecting to secure workspace...</span>
            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                className="ml-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30 transition-all cursor-pointer"
              >
                Skip to Sign In
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Left Sidebar Skeleton ── */}
      <aside className="w-64 border-r border-white/[0.08] bg-[#07120c]/80 backdrop-blur-md flex flex-col h-full flex-shrink-0">
        {/* Header Bar */}
        <div className="h-14 px-5 flex items-center justify-between border-b border-white/[0.08]">
          <div className="h-5 w-28 skeleton-shimmer rounded-md" />
        </div>

        {/* Tab Switcher Area */}
        <div className="p-3 border-b border-white/[0.06]">
          <div className="grid grid-cols-2 gap-1 p-1 bg-white/[0.03] rounded-xl border border-white/[0.06]">
            <div className="h-7 skeleton-shimmer rounded-lg" />
            <div className="h-7 skeleton-shimmer rounded-lg opacity-40" />
          </div>
        </div>

        {/* Action Button Skeleton */}
        <div className="p-3.5 border-b border-white/[0.06]">
          <div className="h-9 w-full skeleton-shimmer rounded-xl" />
        </div>

        {/* Search Bar Skeleton */}
        <div className="px-3 py-2.5 border-b border-white/[0.06]">
          <div className="h-8 w-full skeleton-shimmer rounded-xl" />
        </div>

        {/* Conversations History List Skeleton */}
        <div className="flex-1 p-3 space-y-2.5 overflow-hidden">
          <div className="flex items-center justify-between px-2 mb-2">
            <div className="h-3 w-20 skeleton-shimmer rounded-md" />
            <div className="h-4 w-6 skeleton-shimmer rounded-full" />
          </div>

          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              className="p-3 rounded-xl border border-white/[0.04] bg-white/[0.02] flex items-center gap-3"
            >
              <div className="w-2.5 h-2.5 rounded-full skeleton-shimmer flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div
                  className="h-3 skeleton-shimmer rounded-md"
                  style={{ width: `${55 + n * 10}%` }}
                />
                <div className="h-2 skeleton-shimmer rounded-md w-14" />
              </div>
            </div>
          ))}
        </div>

        {/* User Profile Footer Skeleton */}
        <div className="p-3.5 border-t border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-xl skeleton-shimmer" />
            <div className="space-y-1">
              <div className="h-3 w-20 skeleton-shimmer rounded-md" />
              <div className="h-2 w-14 skeleton-shimmer rounded-md" />
            </div>
          </div>
          <div className="h-6 w-12 skeleton-shimmer rounded-lg" />
        </div>
      </aside>

      {/* ── Main Chat Area Skeleton ── */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#050d08] relative">
        {/* Top Header Bar */}
        <header className="h-14 px-6 border-b border-white/[0.08] bg-[#07120c]/60 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full skeleton-shimmer" />
            <div className="h-4 w-40 skeleton-shimmer rounded-md" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-6 w-24 skeleton-shimmer rounded-full" />
            <div className="h-6 w-28 skeleton-shimmer rounded-full" />
          </div>
        </header>

        {/* Center Content Skeleton (Empty State / Suggestion Grid) */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-3xl mx-auto w-full">
          {/* Hero Question Shimmer */}
          <div className="h-7 w-72 skeleton-shimmer rounded-lg mb-8" />

          {/* 2x2 Suggestion Cards Shimmer */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full mb-10">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="p-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] flex flex-col gap-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg skeleton-shimmer flex-shrink-0" />
                  <div className="h-3.5 w-32 skeleton-shimmer rounded-md" />
                </div>
                <div className="h-3 w-full skeleton-shimmer rounded-md" />
                <div className="h-3 w-4/5 skeleton-shimmer rounded-md" />
              </div>
            ))}
          </div>

          {/* Bottom Chat Input Capsule Shimmer */}
          <div className="w-full h-14 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 flex items-center justify-between">
            <div className="h-4 w-64 skeleton-shimmer rounded-md ml-2" />
            <div className="w-8 h-8 rounded-full skeleton-shimmer" />
          </div>
        </div>
      </main>
    </div>
  );
}
