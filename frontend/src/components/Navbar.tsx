import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { getAuthToken, isMockMode, logout } from '../api/client';

const navLinks = [
  { path: '/', label: 'Dashboard' },
  { path: '/upload', label: 'Upload' },
  { path: '/documents/33333333-3333-3333-3333-333333333333', label: 'Review Demo' },
  { path: '/export', label: 'Export' },
  { path: '/verify', label: 'C1 Verification' },
];

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [openForPath, setOpenForPath] = useState<string | null>(null);
  const menuOpen = openForPath === location.pathname;
  const signedIn = Boolean(getAuthToken());

  const accountAction = signedIn ? (
    <button type="button" onClick={logout} className="text-sm text-slate-300 hover:text-white">
      Sign out
    </button>
  ) : (
    <Link to="/login" onClick={() => setOpenForPath(null)} className="text-sm text-slate-300 hover:text-white">
      Sign in
    </Link>
  );

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex shrink-0 items-center gap-3" onClick={() => setOpenForPath(null)}>
          <span className="w-9 h-9 rounded-md bg-indigo-600 flex items-center justify-center font-bold text-white">
            DF
          </span>
          <span className="font-bold text-lg text-white">DocFlow</span>
        </Link>

        <nav aria-label="Main navigation" className="hidden lg:flex items-center gap-1">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              aria-current={location.pathname === link.path ? 'page' : undefined}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                location.pathname === link.path
                  ? 'bg-indigo-600/30 text-indigo-200'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden lg:flex items-center gap-5">
          {isMockMode() && <span className="text-xs text-amber-300">Demo</span>}
          {accountAction}
        </div>

        <button
          type="button"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          aria-controls="mobile-navigation"
          title={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setOpenForPath(menuOpen ? null : location.pathname)}
          className="lg:hidden inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-slate-200 hover:bg-slate-800"
        >
          {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
        </button>
      </div>

      {menuOpen && (
        <nav id="mobile-navigation" aria-label="Mobile navigation" className="lg:hidden border-t border-slate-800 px-4 py-3 space-y-1">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => setOpenForPath(null)}
              aria-current={location.pathname === link.path ? 'page' : undefined}
              className="block rounded-md px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              {link.label}
            </Link>
          ))}
          <div className="flex items-center justify-between border-t border-slate-800 px-3 pt-3 mt-3">
            {accountAction}
            {isMockMode() && <span className="text-xs text-amber-300">Demo</span>}
          </div>
        </nav>
      )}
    </header>
  );
};
