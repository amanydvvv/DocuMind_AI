import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import AuthModal from '../components/AuthModal';
import * as api from '../services/api';

// Mock the 3D WebGL spheres to avoid Canvas/WebGL dependencies in JSDOM
vi.mock('../components/auth/Interactive3DSpheres', () => ({
  default: () => <div data-testid="interactive-3d-spheres" />,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('AuthModal Component Regressions', () => {
  it('renders distinct 429 rate-limit error message when server responds with 429', async () => {
    const rateLimitError = new Error('Too many requests. Please slow down and try again later.');
    vi.spyOn(api, 'loginUser').mockRejectedValue(rateLimitError);

    const { container } = render(<AuthModal onAuthSuccess={vi.fn()} onAuthError={vi.fn()} />);

    // Fill in credentials
    fireEvent.change(screen.getByPlaceholderText(/e-mail address/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText(/password/i), {
      target: { value: 'ValidPass1234!' },
    });

    // Click Sign In Submit Button
    const submitBtn = container.querySelector('#auth-submit-btn');
    fireEvent.click(submitBtn);

    // Wait for the rate-limit message to be rendered
    await waitFor(() => {
      const el = screen.getByText(/too many requests\. please slow down and try again later\./i);
      expect(el).toBeTruthy();
    });
  });

  it('double-submit guard blocks rapid double-clicking on sign-in button', async () => {
    let resolveLogin;
    const loginPromise = new Promise((resolve) => {
      resolveLogin = resolve;
    });

    const loginSpy = vi.spyOn(api, 'loginUser').mockImplementation(() => loginPromise);

    const { container } = render(<AuthModal onAuthSuccess={vi.fn()} onAuthError={vi.fn()} />);

    // Fill in credentials
    fireEvent.change(screen.getByPlaceholderText(/e-mail address/i), {
      target: { value: 'rapid@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText(/password/i), {
      target: { value: 'ValidPass1234!' },
    });

    const submitBtn = container.querySelector('#auth-submit-btn');

    // Click rapidly multiple times in succession
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    // Assert that loginUser API was dispatched EXACTLY ONCE
    expect(loginSpy).toHaveBeenCalledTimes(1);

    // Resolve the in-flight request
    resolveLogin({ access_token: 'tok_123', user_id: 'uid_1', email: 'rapid@example.com' });

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('double-submit guard also protects the sign-up mode', async () => {
    let resolveSignup;
    const signupPromise = new Promise((resolve) => {
      resolveSignup = resolve;
    });

    const signupSpy = vi.spyOn(api, 'signupUser').mockImplementation(() => signupPromise);

    const { container } = render(<AuthModal onAuthSuccess={vi.fn()} onAuthError={vi.fn()} />);

    // Switch to Sign Up mode via the switcher tab buttons
    const signUpTabs = screen.getAllByRole('button', { name: /sign up/i });
    fireEvent.click(signUpTabs[0]);

    // Fill in credentials
    fireEvent.change(screen.getByPlaceholderText(/e-mail address/i), {
      target: { value: 'newuser@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText(/password/i), {
      target: { value: 'ValidPass1234!' },
    });

    const submitBtn = container.querySelector('#auth-submit-btn');

    // Click rapidly 3 times
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    // Assert that signupUser API was dispatched EXACTLY ONCE
    expect(signupSpy).toHaveBeenCalledTimes(1);

    resolveSignup({ access_token: 'tok_new', user_id: 'uid_2', email: 'newuser@example.com' });

    await waitFor(() => {
      expect(signupSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('forgot-password mode submits and renders confirmation banner', async () => {
    const forgotSpy = vi.spyOn(api, 'requestPasswordReset').mockResolvedValue({
      message: 'If an account exists with this email, password reset instructions have been sent.',
    });

    const { container } = render(<AuthModal onAuthSuccess={vi.fn()} onAuthError={vi.fn()} />);

    // Click "Forgot password?"
    fireEvent.click(screen.getByText(/forgot password\?/i));

    // Enter email
    fireEvent.change(screen.getByPlaceholderText(/e-mail address/i), {
      target: { value: 'forgot@example.com' },
    });

    // Click Send Reset Link
    const submitBtn = container.querySelector('#forgot-submit-btn');
    fireEvent.click(submitBtn);

    expect(forgotSpy).toHaveBeenCalledTimes(1);
    expect(forgotSpy).toHaveBeenCalledWith('forgot@example.com', expect.any(AbortSignal));

    await waitFor(() => {
      const el = screen.getByText(/if an account exists with this email, password reset instructions have been sent\./i);
      expect(el).toBeTruthy();
    });
  });
});
