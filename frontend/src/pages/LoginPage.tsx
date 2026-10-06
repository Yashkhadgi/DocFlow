import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register, getApiErrorMessage } from '../api/client';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('demo@docflow.app');
  const [password, setPassword] = useState('Demo@1234');
  const [fullName, setFullName] = useState('Demo User');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      if (isRegister) {
        await register({ email, password, full_name: fullName });
        await login({ email, password });
      } else {
        await login({ email, password });
      }
      navigate('/');
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err, 'Authentication failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-12 bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-black text-white">
          {isRegister ? 'Create Account' : 'Welcome back to DocFlow'}
        </h2>
        <p className="text-sm text-slate-400">
          {isRegister ? 'Sign up for document processing' : 'Sign in to access your dashboard'}
        </p>
      </div>

      {errorMsg && (
        <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-lg text-rose-300 text-xs">
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {isRegister && (
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Email address</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-lg transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
        >
          {loading ? 'Processing...' : isRegister ? 'Register' : 'Sign In'}
        </button>
      </form>

      <div className="text-center pt-2 border-t border-slate-800">
        <button
          onClick={() => setIsRegister(!isRegister)}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
        >
          {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
        </button>
      </div>
    </div>
  );
};
