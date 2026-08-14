import { useRef, useState } from 'react';
import { loginUser, signupUser } from '../services/api';
import BrandIcon from '../components/shared/BrandIcon';

export default function AuthModal({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const submitInFlight = useRef(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitInFlight.current) return;
    submitInFlight.current = true;
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        const data = await loginUser(email, password);
        onAuthSuccess(data);
      } else {
        const data = await signupUser(email, password);
        onAuthSuccess(data);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      submitInFlight.current = false;
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-screen flex flex-col items-center justify-center p-6 bg-[#08090D] overflow-hidden select-none">
      {/* Dynamic Ambient Mesh & Grid Background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-amber-500/10 via-[#0B0D14] to-[#08090D] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] pointer-events-none opacity-80" />
      
      {/* Top Ambient Glow Rings */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-amber-500/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-emerald-500/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Top Navigation Badge */}
      <div className="relative z-10 mb-8 flex items-center gap-3 px-4 py-1.5 rounded-full bg-[#111319]/80 border border-white/[0.08] shadow-[0_4px_20px_rgba(0,0,0,0.5)] backdrop-blur-xl animate-in fade-in slide-in-from-top-3 duration-300">
        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
        <span className="text-xs font-semibold text-slate-200 tracking-tight">KueryCore Enterprise</span>
        <span className="text-slate-600">•</span>
        <span className="text-[11px] text-amber-400 font-mono font-medium">Hybrid RAG v1.4</span>
      </div>

      {/* Main Flagship Console Card */}
      <div className="relative z-10 w-full max-w-[420px] bg-[#10121A]/85 backdrop-blur-2xl rounded-3xl border border-white/[0.08] p-8 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.8),inset_0_1px_0_0_rgba(255,255,255,0.1)] animate-in fade-in zoom-in-95 duration-300">
        
        {/* Brand Core */}
        <div className="flex flex-col items-center text-center mb-7">
          <div className="relative mb-4">
            <div className="absolute -inset-2 bg-amber-500/20 rounded-2xl blur-lg animate-pulse" />
            <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-b from-[#1E2230] to-[#12141D] border border-amber-500/30 flex items-center justify-center shadow-[0_0_24px_rgba(245,158,11,0.25)]">
              <BrandIcon size={24} />
            </div>
          </div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">
            {isLogin ? 'Sign in to KueryCore' : 'Create your workspace'}
          </h1>
          <p className="text-xs text-slate-400 mt-1.5 leading-relaxed max-w-[280px]">
            {isLogin
              ? 'Enter your credentials to access your secure document knowledge base.'
              : 'Deploy a dedicated vector partition with grounded AI synthesis.'}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex p-1 mb-6 rounded-xl bg-[#090A0F] border border-white/[0.06]">
          <button
            type="button"
            onClick={() => { setIsLogin(true); setError(''); }}
            className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer ${
              isLogin
                ? 'bg-[#1A1E2B] text-slate-100 shadow-sm border border-white/[0.08] font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsLogin(false); setError(''); }}
            className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer ${
              !isLogin
                ? 'bg-[#1A1E2B] text-slate-100 shadow-sm border border-white/[0.08] font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-5 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs font-medium flex items-center gap-2.5 animate-in slide-in-from-top-2 duration-150">
            <span className="text-red-400 text-xs font-bold">◬</span>
            <span className="truncate">{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="auth-email" className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
              Email Address
            </label>
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              placeholder="alex@enterprise.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#0B0D14] border border-white/[0.08] rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/70 focus:ring-2 focus:ring-amber-500/20 transition-all duration-150 shadow-inner"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="auth-password" className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                Password
              </label>
            </div>
            <input
              id="auth-password"
              type="password"
              required
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#0B0D14] border border-white/[0.08] rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/70 focus:ring-2 focus:ring-amber-500/20 transition-all duration-150 shadow-inner"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group mt-2 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-amber-500 hover:from-amber-400 hover:to-amber-300 active:scale-[0.98] text-slate-950 font-bold text-xs tracking-wide shadow-[0_4px_20px_rgba(245,158,11,0.3),inset_0_1px_0_rgba(255,255,255,0.4)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>{loading ? 'Authenticating...' : isLogin ? 'Access Console' : 'Initialize Workspace'}</span>
            <span className="text-xs font-bold transition-transform group-hover:translate-x-1">→</span>
          </button>
        </form>
      </div>

      {/* Bottom Feature Badges */}
      <div className="relative z-10 mt-8 flex flex-wrap items-center justify-center gap-6 text-[11px] text-slate-400 font-medium">
        <span className="flex items-center gap-1.5">
          <span className="text-amber-400 text-xs">◈</span>
          <span>Zero Data Retention</span>
        </span>
        <span className="text-slate-700">•</span>
        <span className="flex items-center gap-1.5">
          <span className="text-amber-400 text-xs">▣</span>
          <span>Hybrid BM25 + Vector Retrieval</span>
        </span>
        <span className="text-slate-700">•</span>
        <span className="flex items-center gap-1.5">
          <span className="text-amber-400 text-xs">⬡</span>
          <span>Presidio PII Redaction</span>
        </span>
      </div>
    </div>
  );
}