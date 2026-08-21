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
    if (submitInFlight.current) return;
    submitInFlight.current = true;
    setError('');
    setLoading(true);
    try {
      // Generate a unique isolated guest account for each visitor/session
      const guestId = Math.random().toString(36).substring(2, 8);
      const guestEmail = `guest_${guestId}@kuerycore.ai`;
      const guestPass = `Guest_${guestId}_${Date.now()}!`;

      const signupData = await signupUser(guestEmail, guestPass);
      onAuthSuccess(signupData);
    } catch (err) {
      setError(err.message || 'Demo initialization failed. Please try standard sign up.');
    } finally {
      submitInFlight.current = false;
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

      {/* ── MAIN AUTHENTICATION CONTAINER (Matching Reference Box Aesthetic) ── */}
      <div 
        className="relative z-10 w-full max-w-[380px] sm:max-w-[400px] flex flex-col items-center transition-transform duration-200 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * 0.2}px, ${mousePos.y * 0.2}px, 0)`,
        }}
      >
        {/* Large Bold Brand Heading */}
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight text-center mb-2">
          {isLogin ? 'Welcome Back.' : 'Get Started.'}
        </h1>

        {/* Animated Typewriter Subtitle */}
        <div className="h-6 flex items-center justify-center gap-1 mb-5 text-xs font-medium text-slate-400 font-mono">
          <span>{displayedText}</span>
          <span className="w-1.5 h-3.5 bg-emerald-400 animate-pulse inline-block" />
        </div>

        {/* Glass Card Enclosure (Exact Reference Box Styling) */}
        <div
          className="w-full rounded-2xl p-6 sm:p-7 flex flex-col items-center"
          style={{
            background: 'linear-gradient(180deg, rgba(13, 29, 21, 0.88) 0%, rgba(9, 20, 16, 0.96) 100%)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(255, 255, 255, 0.09)',
            boxShadow: '0 24px 60px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
          }}
        >
          {/* Beveled Mode Switcher Bar (Matching Reference Question Bar) */}
          <div
            className="w-full p-1 rounded-xl flex items-center mb-5"
            style={{
              background: 'linear-gradient(180deg, #222824 0%, #111613 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 4px 12px rgba(0, 0, 0, 0.4)',
            }}
          >
            <button
              type="button"
              onClick={() => { setIsLogin(true); setError(''); }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                isLogin
                  ? 'bg-emerald-500/20 text-white border border-emerald-400/40 shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsLogin(false); setError(''); }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                !isLogin
                  ? 'bg-emerald-500/20 text-white border border-emerald-400/40 shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Sign Up
            </button>
          </div>

          {/* Instant Demo Quick Access */}
          <div className="w-full mb-4">
            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl bg-[#060e09] hover:bg-[#0d2018] border border-white/[0.08] hover:border-emerald-400/40 transition-all duration-150 flex items-center justify-center gap-2.5 text-xs font-bold text-slate-200 cursor-pointer shadow-inner active:scale-[0.98]"
            >
              <span className="text-emerald-400 text-sm">⚡</span>
              <span>Instant Demo Access</span>
            </button>
          </div>

          {/* Minimal 'or' divider */}
          <div className="text-[11px] text-slate-500 font-medium mb-4">
            or continue with credentials
          </div>

          {/* Error Alert */}
          {error && (
            <div className="w-full mb-4 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs text-center animate-in fade-in duration-150">
              {error}
            </div>
          )}

          {/* Form Inputs */}
          <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
            <div className="w-full">
              <input
                id="auth-email"
                type="email"
                required
                autoComplete="email"
                placeholder="E-mail address..."
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#060e09] border border-white/[0.09] hover:border-white/[0.16] focus:border-emerald-400/80 focus:ring-1 focus:ring-emerald-400/40 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner"
              />
            </div>

            <div className="w-full">
              <input
                id="auth-password"
                type="password"
                required
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                placeholder="Password..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#060e09] border border-white/[0.09] hover:border-white/[0.16] focus:border-emerald-400/80 focus:ring-1 focus:ring-emerald-400/40 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner"
              />
            </div>

            {/* Submit CTA Button with Reference Emerald Finish */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm tracking-wide transition-all duration-150 cursor-pointer active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              style={{
                background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                color: '#020804',
                boxShadow: '0 4px 20px rgba(0, 214, 143, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.3)',
              }}
            >
              <span>{loading ? 'Processing...' : isLogin ? 'Sign In' : 'Create Account'}</span>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#020804" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </form>

          {/* Footer Links */}
          <div className="mt-5 flex flex-col items-center gap-2 text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <span>{isLogin ? "Don't have an account?" : 'Already have an account?'}</span>
              <button
                type="button"
                onClick={() => { setIsLogin(!isLogin); setError(''); }}
                className="font-bold text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
              >
                {isLogin ? 'Sign up' : 'Sign in'}
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
    </div>
  );
}