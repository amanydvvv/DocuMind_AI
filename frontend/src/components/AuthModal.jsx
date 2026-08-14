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
    <div className="relative min-h-screen w-screen flex flex-col items-center justify-center p-4 bg-[#08090D] overflow-hidden select-none">
      {/* Background Architectural Grid & Ambient Aura */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-[radial-gradient(ellipse_50%_40%_at_50%_0%,rgba(245,158,11,0.12),transparent_70%)] pointer-events-none" />

      {/* Top Telemetry Header */}
      <div className="relative z-10 mb-6 flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] backdrop-blur-md shadow-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
        <span className="text-[11px] font-medium text-slate-300 tracking-tight">KueryCore Security Gateway</span>
        <span className="text-slate-600">•</span>
        <span className="text-[11px] text-slate-400 font-mono">v1.4-PRO</span>
      </div>

      {/* Main High-Craft Card */}
      <div className="relative z-10 w-full max-w-[380px] bg-[#0E1017]/90 backdrop-blur-2xl rounded-2xl border border-white/[0.08] p-7 shadow-[0_24px_50px_-12px_rgba(0,0,0,0.85),inset_0_1px_0_0_rgba(255,255,255,0.08)] animate-in fade-in zoom-in-95 duration-200">
        
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-white/[0.04] border border-amber-500/25 mb-3.5 shadow-[0_0_20px_rgba(245,158,11,0.18)]">
            <BrandIcon size={22} />
          </div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight">
            {isLogin ? 'Sign in to KueryCore' : 'Create an Account'}
          </h1>
          <p className="text-xs text-slate-400 mt-1 leading-normal">
            {isLogin
              ? 'Access your private grounded knowledge workspace'
              : 'Start indexing documents with hybrid vector retrieval'}
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 px-3.5 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs font-medium flex items-center gap-2 animate-in slide-in-from-top-1">
            <span className="text-red-400 text-xs">◬</span>
            <span className="truncate">{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="auth-email" className="text-[11px] font-medium text-slate-300 tracking-wide">
              Work Email
            </label>
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              placeholder="name@organization.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#131620] border border-white/[0.08] rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30 transition-all duration-150 shadow-inner"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="auth-password" className="text-[11px] font-medium text-slate-300 tracking-wide">
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
              className="w-full bg-[#131620] border border-white/[0.08] rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30 transition-all duration-150 shadow-inner"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group mt-1 w-full py-2.5 px-4 rounded-xl bg-gradient-to-b from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 active:scale-[0.98] text-slate-950 font-semibold text-xs tracking-tight shadow-[0_2px_12px_rgba(245,158,11,0.3),inset_0_1px_0_rgba(255,255,255,0.4)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span>{loading ? 'Authenticating...' : isLogin ? 'Sign In' : 'Create Workspace'}</span>
            <span className="text-xs font-bold transition-transform group-hover:translate-x-0.5">→</span>
          </button>
        </form>

        {/* Switch mode */}
        <div className="mt-5 pt-4 border-t border-white/[0.06] text-center text-xs flex justify-center items-center gap-1.5">
          <span className="text-slate-400">
            {isLogin ? "Don't have an account?" : 'Already registered?'}
          </span>
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
            className="font-semibold text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
          >
            {isLogin ? 'Sign up' : 'Log in'}
          </button>
        </div>
      </div>

      {/* Bottom Trust Telemetry */}
      <div className="relative z-10 mt-6 flex items-center gap-4 text-[11px] text-slate-500 font-medium">
        <span className="flex items-center gap-1">
          <span className="text-amber-500 text-[10px]">◈</span>
          <span>Zero Data Retention</span>
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <span className="text-amber-500 text-[10px]">▣</span>
          <span>Hybrid Vector Isolation</span>
        </span>
      </div>
    </div>
  );
}