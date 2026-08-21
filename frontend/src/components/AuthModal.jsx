import { useEffect, useRef, useState } from 'react';
import { loginUser, signupUser } from '../services/api';

const ANIMATED_SUBTITLES = [
  'Grounded Document RAG Engine.',
  'Mathematical Citation Proofs.',
  'Automated PII Guardrails.',
  'Sub-350ms Hybrid Search.',
];

export default function AuthModal({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const submitInFlight = useRef(false);

  // Animated typewriter state
  const [subtitleIndex, setSubtitleIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Subtle 3D mouse parallax state
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e) => {
      const { innerWidth, innerHeight } = window;
      const x = (e.clientX / innerWidth - 0.5) * 20; // -10px to +10px
      const y = (e.clientY / innerHeight - 0.5) * 20; // -10px to +10px
      setMousePos({ x, y });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const currentTarget = ANIMATED_SUBTITLES[subtitleIndex];
    const speed = isDeleting ? 30 : 65;

    const timeout = setTimeout(() => {
      if (!isDeleting) {
        if (displayedText.length < currentTarget.length) {
          setDisplayedText(currentTarget.slice(0, displayedText.length + 1));
        } else {
          // Pause before deleting
          setTimeout(() => setIsDeleting(true), 2000);
        }
      } else {
        if (displayedText.length > 0) {
          setDisplayedText(currentTarget.slice(0, displayedText.length - 1));
        } else {
          setIsDeleting(false);
          setSubtitleIndex((prev) => (prev + 1) % ANIMATED_SUBTITLES.length);
        }
      }
    }, speed);

    return () => clearTimeout(timeout);
  }, [displayedText, isDeleting, subtitleIndex]);

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
    setPassword('demo1234567890');
    setError('');
    setLoading(true);
    try {
      const data = await loginUser('demo@kuerycore.ai', 'demo1234567890');
      onAuthSuccess(data);
    } catch {
      try {
        const signupData = await signupUser('demo@kuerycore.ai', 'demo1234567890');
        onAuthSuccess(signupData);
      } catch (err) {
        setError(err.message || 'Demo initialization failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-screen flex flex-col items-center justify-center p-6 overflow-hidden select-none font-sans text-slate-100" style={{ background: '#050d08' }}>
      
      {/* ── 3D VOLUMETRIC FLOATING & ANIMATED SPHERES ── */}
      
      {/* Top Left Floating 3D Magenta-Purple Sphere */}
      <div 
        className="absolute top-[-30px] left-[15%] sm:left-[22%] md:left-[28%] lg:left-[32%] w-36 h-36 sm:w-44 sm:h-44 rounded-full pointer-events-none z-0 animate-float-magenta"
        style={{
          background: 'radial-gradient(circle at 35% 35%, #00ffaa 0%, #00d68f 35%, #00a86b 70%, #003d29 100%)',
          transform: `translate3d(${mousePos.x * -0.6}px, ${mousePos.y * -0.6}px, 0)`,
          transition: 'transform 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      />

      {/* Top Right Floating 3D Matte Graphite Sphere */}
      <div 
        className="absolute top-10 right-[15%] sm:right-[22%] md:right-[28%] lg:right-[32%] w-24 h-24 sm:w-28 sm:h-28 rounded-full pointer-events-none z-0 animate-float-graphite"
        style={{
          background: 'radial-gradient(circle at 35% 35%, #1a3d2b 0%, #0d2018 45%, #091410 80%, #050d08 100%)',
          transform: `translate3d(${mousePos.x * 0.8}px, ${mousePos.y * 0.8}px, 0)`,
          transition: 'transform 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      />

      {/* Micro Floating Ambient Glass Sphere */}
      <div 
        className="absolute bottom-20 left-[18%] w-10 h-10 rounded-full pointer-events-none z-0 animate-float-micro"
        style={{
          background: 'radial-gradient(circle at 35% 35%, rgba(0, 255, 170, 0.6) 0%, rgba(0, 214, 143, 0.2) 60%, transparent 100%)',
          boxShadow: '0 0 20px rgba(0, 214, 143, 0.3)',
          transform: `translate3d(${mousePos.x * 0.4}px, ${mousePos.y * 0.4}px, 0)`,
        }}
      />

      {/* ── MAIN AUTHENTICATION CONTAINER ── */}
      <div 
        className="relative z-10 w-full max-w-[340px] sm:max-w-[360px] flex flex-col items-center mt-12 transition-transform duration-200 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * 0.2}px, ${mousePos.y * 0.2}px, 0)`,
        }}
      >
        
        {/* Large Bold Heading */}
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight text-center">
          {isLogin ? 'Sign In.' : 'Sign Up.'}
        </h1>

        {/* Animated Typewriter Subtitle */}
        <div className="h-6 flex items-center justify-center gap-1 mt-2 mb-7 text-xs font-medium text-slate-400 font-mono">
          <span>{displayedText}</span>
          <span className="w-1.5 h-3.5 bg-emerald-400 animate-pulse inline-block" />
        </div>

        {/* SSO Quick Actions */}
        <div className="w-full flex flex-col gap-3 mb-6">
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full py-3 px-4 rounded-2xl bg-[#091410]/80 hover:bg-[#0d2018] border border-white/[0.08] hover:border-[rgba(0,214,143,0.2)] transition-all duration-150 flex items-center justify-center gap-3 text-xs sm:text-sm font-medium text-slate-200 cursor-pointer shadow-sm active:scale-[0.98]"
          >
            {/* Google 'G' Icon */}
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"/>
              <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/>
              <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/>
              <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"/>
            </svg>
            <span>Continue with Google</span>
          </button>

          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full py-3 px-4 rounded-2xl bg-[#091410]/80 hover:bg-[#0d2018] border border-white/[0.08] hover:border-[rgba(0,214,143,0.2)] transition-all duration-150 flex items-center justify-center gap-3 text-xs sm:text-sm font-medium text-slate-200 cursor-pointer shadow-sm active:scale-[0.98]"
          >
            <span className="text-sm">⚡</span>
            <span>Instant Demo Access</span>
          </button>
        </div>

        {/* Minimal 'or' divider */}
        <div className="text-xs text-slate-500 font-medium mb-6">
          or
        </div>

        {/* Error Alert */}
        {error && (
          <div className="w-full mb-4 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs text-center animate-in fade-in duration-150">
            {error}
          </div>
        )}

        {/* Form Inputs */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3.5">
          <div className="w-full">
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              placeholder="E-mail"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#091410] border border-white/[0.08] hover:border-white/[0.14] focus:border-emerald-400/80 focus:ring-1 focus:ring-emerald-400/40 rounded-2xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner"
            />
          </div>

          <div className="w-full">
            <input
              id="auth-password"
              type="password"
              required
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#091410] border border-white/[0.08] hover:border-white/[0.14] focus:border-emerald-400/80 focus:ring-1 focus:ring-emerald-400/40 rounded-2xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner"
            />
          </div>

          {/* Hero Magenta Gradient CTA Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-3 py-3.5 px-4 rounded-2xl font-bold text-xs sm:text-sm text-white tracking-wide transition-all duration-150 cursor-pointer shadow-[0_4px_24px_rgba(0,214,143,0.35),inset_0_1px_0_rgba(255,255,255,0.25)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, #00a86b 0%, #00d68f 50%, #00ffaa 100%)',
              color: '#030a06',
            }}
          >
            {loading ? 'Signing in...' : isLogin ? 'Sign In.' : 'Sign Up.'}
          </button>
        </form>

        {/* Footer Links */}
        <div className="mt-8 flex flex-col items-center gap-2 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <span>{isLogin ? "don't have an account?" : 'already have an account?'}</span>
            <button
              type="button"
              onClick={() => { setIsLogin(!isLogin); setError(''); }}
              className="font-bold text-white hover:text-emerald-400 transition-colors cursor-pointer"
            >
              {isLogin ? 'Create a account' : 'Sign in'}
            </button>
          </div>

          {isLogin && (
            <button
              type="button"
              onClick={() => setError('Password reset instructions sent to your email.')}
              className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
            >
              Forgot password?
            </button>
          )}
        </div>

      </div>
    </div>
  );
}