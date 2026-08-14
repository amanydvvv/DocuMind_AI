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
      setError(err.message || 'Authentication failed. Please verify your credentials.');
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
      // Fallback try signup if demo user doesn't exist
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
    <div className="min-h-screen w-screen bg-[#07080C] flex items-stretch overflow-x-hidden font-sans text-slate-100 selection:bg-amber-500/30">
      
      {/* ── LEFT HERO SHOWCASE PANEL (Desktop: 7 cols / Mobile: hidden) ── */}
      <div className="hidden lg:flex lg:w-7/12 relative flex-col justify-between p-12 xl:p-16 overflow-hidden bg-gradient-to-br from-[#0D0F18] via-[#090A10] to-[#050608] border-r border-white/[0.06]">
        
        {/* Ambient Gradient Orbs & Subtle Grid */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-amber-500/10 rounded-full blur-[140px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[600px] h-[600px] bg-amber-600/10 rounded-full blur-[160px] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

        {/* Top Brand Pill */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400/20 to-amber-600/10 border border-amber-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(245,158,11,0.2)]">
            <BrandIcon size={22} />
          </div>
          <div>
            <div className="text-base font-extrabold tracking-tight text-white flex items-center gap-2">
              KueryCore <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">Enterprise</span>
            </div>
            <p className="text-xs text-slate-400">Grounded Document RAG Engine</p>
          </div>
        </div>

        {/* Center Hero Typography & Feature Cards */}
        <div className="relative z-10 my-auto py-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] backdrop-blur-md mb-6 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-medium text-slate-300">Production-Ready Hybrid Intelligence</span>
          </div>

          <h2 className="text-3xl xl:text-4xl 2xl:text-5xl font-black text-white tracking-tight leading-[1.15] max-w-xl">
            Query deep archives with <span className="bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 bg-clip-text text-transparent">verifiable mathematical precision</span>.
          </h2>

          <p className="text-sm xl:text-base text-slate-400 mt-4 leading-relaxed max-w-lg">
            Zero hallucinations. Dual BM25 sparse keyword ranking combined with pgvector dense embeddings, real-time OCR extraction, and PII guardrails.
          </p>

          {/* Interactive Showcase Cards */}
          <div className="grid sm:grid-cols-2 gap-4 mt-8 max-w-xl">
            {/* Card 1 */}
            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-xl hover:border-amber-500/30 transition-all duration-200">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 text-xs font-bold">
                  ◈
                </div>
                <h4 className="text-xs font-bold text-slate-200">Hybrid Retrieval</h4>
              </div>
              <p className="text-[11px] text-slate-400 leading-normal">
                Reciprocal Rank Fusion blends BM25 lexical search and cosine semantic embeddings.
              </p>
            </div>

            {/* Card 2 */}
            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-xl hover:border-amber-500/30 transition-all duration-200">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs font-bold">
                  ⬡
                </div>
                <h4 className="text-xs font-bold text-slate-200">Presidio PII Shield</h4>
              </div>
              <p className="text-[11px] text-slate-400 leading-normal">
                Automated regex and NLP scrubbing redacts sensitive records prior to model ingress.
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-xl hover:border-amber-500/30 transition-all duration-200">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-xs font-bold">
                  ▣
                </div>
                <h4 className="text-xs font-bold text-slate-200">Page-Exact Citations</h4>
              </div>
              <p className="text-[11px] text-slate-400 leading-normal">
                Every generated claim binds directly to an inspectable PDF page coordinate snippet.
              </p>
            </div>

            {/* Card 4 */}
            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-xl hover:border-amber-500/30 transition-all duration-200">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 text-xs font-bold">
                  ⚡
                </div>
                <h4 className="text-xs font-bold text-slate-200">Instant Vector Engine</h4>
              </div>
              <p className="text-[11px] text-slate-400 leading-normal">
                Sub-350ms multi-hop synthesis with fallback cascades across Groq and Gemini models.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Trust & Compliance Bar */}
        <div className="relative z-10 pt-6 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="text-amber-400">✓</span> <span>Zero Data Retention</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-amber-400">✓</span> <span>SOC-2 Type II Schema</span>
            </span>
          </div>
          <span className="font-mono text-[11px] text-slate-400">v1.4.0 • Enterprise Core</span>
        </div>
      </div>

      {/* ── RIGHT AUTHENTICATION PANEL (Desktop: 5 cols / Mobile: full screen) ── */}
      <div className="w-full lg:w-5/12 flex flex-col justify-between p-6 sm:p-10 xl:p-14 bg-[#090B10] overflow-y-auto">
        
        {/* Mobile Header (Only visible on small viewports) */}
        <div className="flex lg:hidden items-center justify-between pb-6 border-b border-white/[0.06] mb-6">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
              <BrandIcon size={18} />
            </div>
            <span className="text-base font-bold text-white tracking-tight">KueryCore AI</span>
          </div>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
            Enterprise
          </span>
        </div>

        {/* Main Auth Form Container */}
        <div className="my-auto w-full max-w-md mx-auto py-4">
          
          {/* Header Title */}
          <div className="mb-6">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1.5">
              {isLogin
                ? 'Sign in to access your grounded document workspaces and threads.'
                : 'Get started with high-precision enterprise document retrieval.'}
            </p>
          </div>

          {/* Quick Demo Access Bar (Recruiter / Fast Trial Friendly) */}
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full mb-6 p-3 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-400/5 to-amber-500/10 border border-amber-500/30 hover:border-amber-400/60 transition-all duration-200 flex items-center justify-between group cursor-pointer"
          >
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-amber-400/20 flex items-center justify-center text-amber-300 text-xs font-bold">
                ⚡
              </div>
              <div className="text-left">
                <div className="text-xs font-bold text-slate-200 group-hover:text-white flex items-center gap-1.5">
                  Instant Demo Access <span className="text-[10px] text-amber-400 font-normal">(1-Click)</span>
                </div>
                <div className="text-[10px] text-slate-400">Explore preloaded RAG indexes without setup</div>
              </div>
            </div>
            <span className="text-xs font-bold text-amber-400 group-hover:translate-x-1 transition-transform">→</span>
          </button>

          {/* Divider with Segmented Tabs */}
          <div className="flex items-center gap-3 mb-6">
            <div className="h-px flex-1 bg-white/[0.08]" />
            <div className="flex p-1 rounded-xl bg-white/[0.04] border border-white/[0.08]">
              <button
                type="button"
                onClick={() => { setIsLogin(true); setError(''); }}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  isLogin ? 'bg-[#191D28] text-white shadow-sm border border-white/[0.08]' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setIsLogin(false); setError(''); }}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  !isLogin ? 'bg-[#191D28] text-white shadow-sm border border-white/[0.08]' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Register
              </button>
            </div>
            <div className="h-px flex-1 bg-white/[0.08]" />
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs flex items-center gap-2.5 animate-in fade-in duration-150">
              <span className="text-red-400 font-bold text-sm">◬</span>
              <span className="flex-1">{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            
            {/* Email Field */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="auth-email" className="text-xs font-semibold text-slate-300">
                Work Email Address
              </label>
              <div className="relative">
                <input
                  id="auth-email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="analyst@enterprise.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-[#11141D] border border-white/[0.08] rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/80 focus:ring-2 focus:ring-amber-500/20 transition-all duration-150 shadow-inner"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="auth-password" className="text-xs font-semibold text-slate-300">
                  Password
                </label>
                {isLogin && (
                  <span className="text-[11px] text-slate-500 hover:text-amber-400 cursor-pointer transition-colors">
                    Forgot password?
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  id="auth-password"
                  type="password"
                  required
                  autoComplete={isLogin ? 'current-password' : 'new-password'}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#11141D] border border-white/[0.08] rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/80 focus:ring-2 focus:ring-amber-500/20 transition-all duration-150 shadow-inner"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full py-3.5 px-5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-amber-500 hover:from-amber-400 hover:to-amber-300 active:scale-[0.99] text-slate-950 font-bold text-xs sm:text-sm tracking-wide shadow-[0_4px_24px_rgba(245,158,11,0.3),inset_0_1px_0_rgba(255,255,255,0.4)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>{loading ? 'Authenticating...' : isLogin ? 'Sign In to Workspace' : 'Create Enterprise Account'}</span>
              <span className="font-bold">→</span>
            </button>
          </form>

          {/* Social / SSO Alternative Placeholders */}
          <div className="mt-6 pt-5 border-t border-white/[0.06] text-center">
            <div className="text-xs text-slate-400">
              {isLogin ? "Don't have an account yet?" : 'Already have an existing workspace?'}
              <button
                type="button"
                onClick={() => { setIsLogin(!isLogin); setError(''); }}
                className="ml-1.5 font-bold text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
              >
                {isLogin ? 'Sign up' : 'Log in'}
              </button>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="pt-6 text-center lg:text-left text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.06]">
          <span>© 2026 KueryCore AI Inc. All rights reserved.</span>
          <div className="flex items-center gap-3">
            <span className="hover:text-slate-300 transition-colors cursor-pointer">Privacy</span>
            <span>•</span>
            <span className="hover:text-slate-300 transition-colors cursor-pointer">Terms</span>
            <span>•</span>
            <span className="hover:text-slate-300 transition-colors cursor-pointer">Security</span>
          </div>
        </div>

      </div>
    </div>
  );
}