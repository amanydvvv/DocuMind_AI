import { useRef, useState } from 'react';
import { loginUser, signupUser } from '../services/api';
import BrandIcon from './shared/BrandIcon';

export default function AuthModal({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const submitInFlight = useRef(false);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
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
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      submitInFlight.current = false;
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setEmail('demo@kuerycore.ai');
    setPassword('demo1234');
    setError('');
    setLoading(true);
    try {
      const data = await loginUser('demo@kuerycore.ai', 'demo1234');
      onAuthSuccess(data);
    } catch {
      try {
        const signupData = await signupUser('demo@kuerycore.ai', 'demo1234');
        onAuthSuccess(signupData);
      } catch (err) {
        setError(err.message || 'Demo initialization failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-screen bg-[#090A0E] flex items-stretch font-sans text-zinc-100 selection:bg-zinc-700">
      
      {/* ── LEFT EDITORIAL LEDGER (Desktop: 6.5 cols / Mobile: hidden) ── */}
      <div className="hidden lg:flex lg:w-7/12 flex-col justify-between p-14 xl:p-20 bg-[#07080B] border-r border-white/[0.06] relative">
        
        {/* Brand Lockup */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-white/[0.08] flex items-center justify-center">
            <BrandIcon size={18} />
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-200">KueryCore</span>
        </div>

        {/* Center Minimal Copy & Ledger */}
        <div className="my-auto max-w-lg py-8">
          <h2 className="text-3xl xl:text-4xl font-semibold tracking-tight text-white leading-tight">
            Grounded retrieval with mathematical citations.
          </h2>
          <p className="text-sm text-zinc-400 mt-4 leading-relaxed font-normal">
            Dual BM25 sparse keyword ranking blended with dense vector embeddings, real-time OCR extraction, and automated PII redaction.
          </p>

          {/* Minimal Specs Ledger */}
          <div className="mt-10 space-y-3 font-mono text-xs text-zinc-400">
            <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04]">
              <span className="text-zinc-500">Retrieval Pipeline</span>
              <span className="text-zinc-300 font-medium">Reciprocal Rank Fusion</span>
            </div>
            <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04]">
              <span className="text-zinc-500">Guardrails</span>
              <span className="text-zinc-300 font-medium">Presidio NLP & Regex Scrubbing</span>
            </div>
            <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04]">
              <span className="text-zinc-500">Vector Isolation</span>
              <span className="text-zinc-300 font-medium">PostgreSQL / pgvector Partitioning</span>
            </div>
            <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04]">
              <span className="text-zinc-500">Citation Mode</span>
              <span className="text-zinc-300 font-medium">Bounding-Box PDF Anchors</span>
            </div>
          </div>
        </div>

        {/* Minimal Footer System Status */}
        <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-6 border-t border-white/[0.04]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Systems Operational</span>
          </div>
          <span>v1.4.0</span>
        </div>
      </div>

      {/* ── RIGHT MINIMAL AUTHENTICATION PANEL ── */}
      <div className="w-full lg:w-5/12 flex flex-col justify-between p-8 sm:p-14 xl:p-20 bg-[#090A0E] overflow-y-auto">
        
        {/* Mobile Brand (Only on mobile) */}
        <div className="flex lg:hidden items-center gap-2.5 mb-8">
          <div className="w-7 h-7 rounded-lg bg-zinc-900 border border-white/[0.08] flex items-center justify-center">
            <BrandIcon size={16} />
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-200">KueryCore</span>
        </div>

        {/* Center Authentication Console */}
        <div className="my-auto w-full max-w-sm mx-auto">
          
          {/* Header & Tabs */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              {isLogin ? 'Sign in' : 'Create workspace'}
            </h1>
            <p className="text-xs text-zinc-400 mt-1.5">
              {isLogin ? 'Enter your credentials to access threads' : 'Get started with high-precision document indexing'}
            </p>
          </div>

          {/* Quick 1-Click Demo Button */}
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full mb-6 py-2.5 px-3.5 rounded-xl bg-zinc-900/90 hover:bg-zinc-800/90 border border-white/[0.08] hover:border-white/[0.16] transition-all duration-150 flex items-center justify-between group cursor-pointer text-xs"
          >
            <span className="text-zinc-300 font-medium group-hover:text-white">Quick Demo Access</span>
            <span className="font-mono text-[11px] text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all">1-click →</span>
          </button>

          {/* Segmented Switcher */}
          <div className="flex p-0.5 mb-6 rounded-lg bg-zinc-900 border border-white/[0.06]">
            <button
              type="button"
              onClick={() => { setIsLogin(true); setError(''); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-150 cursor-pointer ${
                isLogin ? 'bg-[#181920] text-white shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsLogin(false); setError(''); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-150 cursor-pointer ${
                !isLogin ? 'bg-[#181920] text-white shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Register
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-red-950/40 border border-red-800/40 text-red-300 text-xs flex items-center gap-2">
              <span className="font-mono text-red-400">!</span>
              <span className="truncate">{error}</span>
            </div>
          )}

          {/* Minimal Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="auth-email" className="text-xs font-medium text-zinc-300">
                Email
              </label>
              <input
                id="auth-email"
                type="email"
                required
                autoComplete="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#121318] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 transition-all duration-150"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="auth-password" className="text-xs font-medium text-zinc-300">
                Password
              </label>
              <input
                id="auth-password"
                type="password"
                required
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#121318] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 transition-all duration-150"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full py-2.5 px-4 btn-primary text-xs font-semibold tracking-tight disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <span>{loading ? 'Authenticating...' : isLogin ? 'Sign in' : 'Create account'}</span>
              <span className="text-xs font-normal">→</span>
            </button>
          </form>
        </div>

        {/* Minimal Footer */}
        <div className="pt-6 text-center text-[11px] text-zinc-500 font-mono flex items-center justify-between border-t border-white/[0.04]">
          <span>KueryCore AI</span>
          <span>Encrypted Gateway</span>
        </div>

      </div>
    </div>
  );
}