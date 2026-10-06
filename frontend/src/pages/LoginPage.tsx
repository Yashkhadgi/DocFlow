import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login, register } from '../api/client';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useToast } from '../components/Toast';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('elena@docflow.io');
  const [password, setPassword] = useState('••••••••••••');
  const [fullName, setFullName] = useState('Elena Rostova');
  const [loading, setLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      if (isRegister) {
        await register({ email, password, full_name: fullName });
        setSuccessBanner('Account created successfully! Verification sent.');
        toast.success('Account created!');
        setIsRegister(false);
      } else {
        await login({ email, password });
        toast.success('Signed in successfully!');
        navigate('/');
      }
    } catch (err: any) {
      setErrorBanner(err?.error?.message || err?.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FBF9F5] flex flex-col justify-between p-4 sm:p-6 text-[#1C1917] font-sans">
      {/* Top Navbar */}
      <header className="flex justify-between items-center max-w-6xl w-full mx-auto text-xs text-[#78716C]">
        <Link to="/" className="flex items-center space-x-1.5 hover:text-[#1C1917]">
          <span>&larr; Back to website</span>
        </Link>
        <div className="flex items-center space-x-6">
          <a href="#docs" className="hover:text-[#1C1917] flex items-center space-x-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span>Documentation</span>
          </a>
          <a href="#support" className="hover:text-[#1C1917]">Support</a>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-md w-full mx-auto my-8 space-y-4">
        {/* Brand Logo Header */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center space-x-2">
            <div className="w-6 h-6 bg-[#BD3A17] flex items-center justify-center text-white text-xs font-bold">
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              </svg>
            </div>
            <span className="font-extrabold text-xl font-serif-title tracking-tight text-[#1C1917]">
              DocFlow
            </span>
          </div>
          {isRegister && (
            <div className="text-[10px] uppercase font-mono tracking-widest text-[#A8A29E]">
              AP ENGINE v2.4
            </div>
          )}
        </div>

        {/* Card Form Box */}
        <div className="bg-white border border-[#E5E2DA] p-8 shadow-xs rounded-none space-y-6">
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold font-serif-title text-[#1C1917]">
              {isRegister ? 'Create your account' : 'Sign in'}
            </h1>
            <p className="text-xs text-[#78716C]">
              {isRegister
                ? 'Automate invoice extraction, 3-way matching, and fraud protection.'
                : 'Enter your credentials to access your document pipeline.'}
            </p>
          </div>

          {/* Banners */}
          {errorBanner && (
            <div className="p-3 bg-[#FCE8E6] border border-[#FAD2CF] text-[#C5221F] text-xs flex justify-between items-start">
              <div>
                <div className="font-bold">Invalid email or password</div>
                <div className="text-[11px] mt-0.5">{errorBanner}</div>
              </div>
              <button onClick={() => setErrorBanner(null)} className="text-[#C5221F] font-bold">&times;</button>
            </div>
          )}

          {successBanner && (
            <div className="p-3 bg-[#E6F4EA] border border-[#CEEAD6] text-[#137333] text-xs flex justify-between items-start">
              <div>
                <div className="font-bold">{successBanner}</div>
                <div className="text-[11px] mt-0.5">Please sign in to proceed with your setup.</div>
              </div>
              <button onClick={() => setSuccessBanner(null)} className="text-[#137333] font-bold">&times;</button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-left">
            {isRegister && (
              <Input
                label="Full Name"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Elena Rostova"
              />
            )}

            <Input
              label={isRegister ? 'Work Email' : 'Email address'}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="elena@docflow.io"
            />

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-[#44403C] uppercase tracking-wider select-none font-sans">
                  Password
                </label>
                {!isRegister && (
                  <a href="#forgot" className="text-[11px] text-[#78716C] hover:text-[#BD3A17]">
                    Forgot password?
                  </a>
                )}
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full border border-[#D5D1C8] text-sm text-[#1C1917] bg-white py-2.5 px-3 focus:outline-none focus:border-[#BD3A17] rounded-none font-sans"
              />
              {isRegister && (
                <p className="text-[11px] text-[#A8A29E] mt-1">Minimum 8 characters</p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="remember"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 accent-[#BD3A17] rounded-none border-[#D5D1C8]"
              />
              <label htmlFor="remember" className="text-xs text-[#57534E] select-none">
                {isRegister
                  ? 'I agree to the Terms of Service and acknowledge the Privacy Policy.'
                  : 'Remember this device for 30 days'}
              </label>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              isLoading={loading}
              className="mt-2 text-sm uppercase tracking-wider"
            >
              {isRegister ? 'Create account \u2192' : 'Sign in'}
            </Button>
          </form>

          {!isRegister && (
            <>
              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-[#E5E2DA]"></div>
                <span className="flex-shrink mx-4 text-[10px] uppercase font-mono text-[#A8A29E]">OR</span>
                <div className="flex-grow border-t border-[#E5E2DA]"></div>
              </div>

              <Button
                variant="outline"
                size="md"
                fullWidth
                onClick={() => toast.info('SSO SAML authentication initialized')}
                className="text-xs font-normal"
              >
                <svg className="w-4 h-4 mr-2 text-[#78716C]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m3 0h1m-1-4h.01M9 16h.01M9 12h.01M9 8h.01M15 16h.01M15 12h.01M15 8h.01" />
                </svg>
                Single Sign-On (SAML / Okta)
              </Button>
            </>
          )}

          <div className="text-center pt-2 text-xs">
            {isRegister ? (
              <button
                onClick={() => setIsRegister(false)}
                className="text-[#BD3A17] hover:underline font-semibold"
              >
                Already have an account? Sign in &rarr;
              </button>
            ) : (
              <span className="text-[#78716C]">
                Don't have an account?{' '}
                <button
                  onClick={() => setIsRegister(true)}
                  className="text-[#BD3A17] hover:underline font-semibold"
                >
                  Create an account
                </button>
              </span>
            )}
          </div>
        </div>

        {/* Footer info under card */}
        <div className="text-center text-[11px] text-[#A8A29E] font-mono">
          {isRegister
            ? '256-bit SOC 2 Type II certified encryption \u2022 AML/Fraud protection'
            : 'DocFlow Cloud v4.18.2'}
        </div>
      </main>

      {/* Global Footer */}
      <footer className="flex flex-col sm:flex-row justify-between items-center max-w-6xl w-full mx-auto text-[11px] text-[#A8A29E] pt-4 border-t border-[#E5E2DA] gap-2">
        <div>&copy; 2025 DocFlow Technologies Inc. All rights reserved.</div>
        <div className="flex space-x-4">
          <a href="#terms" className="hover:text-[#57534E]">Terms of Service</a>
          <a href="#privacy" className="hover:text-[#57534E]">Privacy Policy</a>
          <a href="#security" className="hover:text-[#57534E]">Security</a>
          <a href="#help" className="hover:text-[#57534E]">Help</a>
        </div>
      </footer>
    </div>
  );
};
