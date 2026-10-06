import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { isMockMode } from '../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const mockActive = isMockMode();

  const navLinks = [
    { path: '/', label: 'Dashboard' },
    { path: '/upload', label: 'Upload' },
    { path: '/documents/33333333-3333-3333-3333-333333333333', label: 'Review Demo' },
    { path: '/export', label: 'Export' },
    { path: '/verify', label: 'C1 Verification' },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-slate-100 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              DF
            </div>
            <span className="font-extrabold text-xl tracking-tight text-white group-hover:text-indigo-300 transition-colors">
              DocFlow
            </span>
          </Link>

          <nav className="hidden md:flex space-x-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800 text-xs">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                mockActive ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'
              }`}
            />
            <span className="text-slate-300 font-mono">
              VITE_USE_MOCK: <strong className={mockActive ? 'text-amber-400' : 'text-emerald-400'}>{mockActive ? 'true' : 'false'}</strong>
            </span>
          </div>

          <Link
            to="/login"
            className="text-xs font-semibold text-slate-400 hover:text-white px-3 py-1.5 rounded-md hover:bg-slate-800 transition-colors"
          >
            Login / Auth
          </Link>
        </div>
      </div>
    </header>
  );
};
