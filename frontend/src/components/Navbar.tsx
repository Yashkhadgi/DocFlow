import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { isMockMode } from '../api/client';
import { Badge } from './Badge';

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
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-40 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white shadow-sm shadow-indigo-600/30 group-hover:scale-105 transition-transform">
              DF
            </div>
            <span className="font-extrabold text-xl tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
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
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-bold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <Badge
            variant={mockActive ? 'amber' : 'green'}
            dot
            size="md"
            className="font-mono"
          >
            VITE_USE_MOCK: <strong>{mockActive ? 'true' : 'false'}</strong>
          </Badge>

          <Link
            to="/login"
            className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors border border-slate-200/60"
          >
            Sign In
          </Link>
        </div>
      </div>
    </header>
  );
};
