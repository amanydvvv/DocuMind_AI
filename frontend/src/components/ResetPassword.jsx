/**
 * ResetPassword.jsx
 * Route: /reset-password?token=<raw_token>
 *
 * Reads the raw token from the URL search params, shows two password fields
 * (new + confirm) with client-side validation, and calls POST /api/auth/reset-password.
 *
 * On success: shows confirmation + navigates to sign-in (does NOT auto-login).
 * On error: shows the generic backend message + a link to request a new email.
 */

import { useState, useRef, useEffect } from 'react';
import { resetPassword } from '../services/api';
import Interactive3DSpheres from './auth/Interactive3DSpheres';

export default function ResetPassword({ onNavigateToSignIn }) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState('');
  const submitInFlight = useRef(false);

  // Extract token from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get('token') || '';
    setToken(t);
    if (!t) {
      setError('No reset token found. Please request a new password reset link.');
    }
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (submitInFlight.current) return;

    // Client-side validation
    if (newPassword.length < 12) {
      setError('Password must be at least 12 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    submitInFlight.current = true;
    setError('');
    setSuccessMsg('');
    setLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15_000);

    try {
      const result = await resetPassword(token, newPassword, controller.signal);
      clearTimeout(timeoutId);
      setSuccessMsg(result.message || 'Password updated successfully. Please sign in with your new password.');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      clearTimeout(timeoutId);
      const isTimeout = err.name === 'AbortError' || /aborted/i.test(err.message);
      setError(
        isTimeout
          ? 'Request timed out. Please try again.'
          : err.message || 'Invalid or expired reset link.'
      );
    } finally {
      setLoading(false);
      submitInFlight.current = false;
    }
  };

  const isExpiredOrInvalid = !token || (error && /invalid|expired/i.test(error));
  const isSuccess = Boolean(successMsg);

  return (
    <div className="relative min-h-screen w-screen flex flex-col items-center justify-center p-6 overflow-hidden select-none font-sans text-slate-100 bg-[#050d08]">
      
      <Interactive3DSpheres />

      <div className="relative z-10 w-full max-w-[390px] sm:max-w-[410px] flex flex-col items-center">

        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight text-center mb-2">
          {isSuccess ? 'All done.' : 'New Password.'}
        </h1>
        <p className="text-xs text-slate-400 font-mono mb-5">
          {isSuccess ? 'Your password has been updated.' : 'Choose a strong password (12+ characters).'}
        </p>

        <div
          className="w-full rounded-2xl p-6 sm:p-7 flex flex-col items-center relative"
          style={{
            background: 'linear-gradient(180deg, rgba(13, 29, 21, 0.9) 0%, rgba(9, 20, 16, 0.98) 100%)',
            backdropFilter: 'blur(28px)',
            WebkitBackdropFilter: 'blur(28px)',
            border: '1px solid rgba(0, 255, 170, 0.2)',
            boxShadow: '0 24px 70px rgba(0, 0, 0, 0.85), 0 0 60px rgba(0, 214, 143, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
          }}
        >
          {/* Error banner */}
          {error && (
            <div className="w-full mb-4 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs text-center">
              {error}
            </div>
          )}

          {/* Success banner */}
          {successMsg && (
            <div className="w-full mb-5 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs text-center">
              <div className="text-2xl mb-2">✓</div>
              {successMsg}
            </div>
          )}

          {/* Form — hidden after success */}
          {!isSuccess && (
            <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
              <input
                id="reset-new-password"
                type="password"
                required
                autoComplete="new-password"
                placeholder="New password (12+ characters)..."
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={!token}
                className="w-full bg-[#060e09] border border-white/[0.09] hover:border-emerald-400/40 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/40 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner disabled:opacity-40"
              />
              <input
                id="reset-confirm-password"
                type="password"
                required
                autoComplete="new-password"
                placeholder="Confirm new password..."
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={!token}
                className="w-full bg-[#060e09] border border-white/[0.09] hover:border-emerald-400/40 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/40 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner disabled:opacity-40"
              />

              <button
                type="submit"
                disabled={loading || !token}
                id="reset-submit-btn"
                className="w-full mt-2 py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm tracking-wide transition-all duration-150 cursor-pointer active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                style={{
                  background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                  color: '#020804',
                  boxShadow: '0 0 35px rgba(0, 214, 143, 0.65), 0 4px 16px rgba(0, 255, 170, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.4)',
                }}
              >
                <span>{loading ? 'Saving...' : 'Set New Password'}</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#020804" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </form>
          )}

          {/* Post-success: navigate to sign-in */}
          {isSuccess && (
            <button
              type="button"
              onClick={onNavigateToSignIn}
              className="w-full mt-2 py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm tracking-wide transition-all duration-150 cursor-pointer active:scale-[0.98] flex items-center justify-center gap-2"
              style={{
                background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                color: '#020804',
                boxShadow: '0 0 35px rgba(0, 214, 143, 0.65), 0 4px 16px rgba(0, 255, 170, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.4)',
              }}
            >
              <span>Sign In Now</span>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#020804" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          )}

          {/* Error state — link to request new email */}
          {isExpiredOrInvalid && (
            <div className="mt-4 text-center text-xs text-slate-500">
              Reset link expired or invalid?{' '}
              <button
                type="button"
                onClick={onNavigateToSignIn}
                className="text-emerald-400 hover:text-emerald-300 font-bold transition-colors cursor-pointer"
              >
                Request a new one
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
