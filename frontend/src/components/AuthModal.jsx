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

  const inputClass =
    'w-full border border-border rounded-xl bg-background/80 px-3.5 py-2.5 text-xs text-text ' +
    'placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary-border ' +
    'focus:border-primary transition-all duration-150 shadow-inner';

  return (
    <div className="fixed inset-0 z-[9999] bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-[390px] glass-card-elevated rounded-3xl p-7 animate-in zoom-in-95 duration-200">
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3">
            <div className="w-12 h-12 rounded-2xl bg-surface-muted border border-primary-border flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.2)]">
              <BrandIcon size={24} />
            </div>
          </div>
          <h2 className="text-lg font-semibold text-text tracking-tight">KueryCore AI</h2>
          <p className="text-xs text-text-muted mt-1 leading-normal">
            {isLogin
              ? 'Enter your credentials to enter the workspace'
              : 'Create an account to start grounded document indexing'}
          </p>
        </div>

        {error && (
          <div className="bg-danger-soft border border-danger-border rounded-xl px-3 py-2 text-xs text-danger-text mb-4 animate-in slide-in-from-top-1">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="auth-email" className="text-[11px] font-medium text-text-secondary">
              Email Address
            </label>
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              placeholder="user@organization.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="auth-password" className="text-[11px] font-medium text-text-secondary">
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              required
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 py-2.5 bg-primary text-white font-semibold rounded-xl text-xs hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 tactile-btn cursor-pointer shadow-[0_2px_12px_rgba(79,70,229,0.3),inset_0_1px_0_0_rgba(255,255,255,0.2)]"
          >
            {loading ? 'Authenticating...' : isLogin ? 'Sign In' : 'Create Workspace'}
          </button>
        </form>

        <div className="mt-5 text-center text-xs flex justify-center items-center gap-1.5 pt-4 border-t border-border-subtle">
          <span className="text-text-muted">
            {isLogin ? "Need an account?" : 'Already registered?'}
          </span>
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
            className="font-semibold text-primary-light hover:text-primary transition-colors cursor-pointer"
          >
            {isLogin ? 'Sign Up' : 'Log In'}
          </button>
        </div>
      </div>
    </div>
  );
}