import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { isMockMode, logout } from '../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const mockActive = isMockMode();

  return (
    <header className="bg-white border-b border-[#E5E2DA] sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Left branding and navigation tabs */}
        <div className="flex items-center space-x-8 h-full">
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#BD3A17] flex items-center justify-center text-white text-xs font-bold rounded-none">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              </svg>
            </div>
            <span className="font-extrabold text-lg tracking-tight text-[#1C1917] font-serif-title">
              DocFlow
            </span>
          </Link>

          <nav className="flex space-x-6 h-full text-xs font-semibold">
            <Link
              to="/"
              className={`h-full flex items-center px-1 border-b-2 transition-colors ${
                location.pathname === '/' || location.pathname.startsWith('/documents')
                  ? 'border-[#BD3A17] text-[#BD3A17] font-bold'
                  : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              Documents
            </Link>
            <Link
              to="/upload"
              className={`h-full flex items-center px-1 border-b-2 transition-colors ${
                location.pathname === '/upload'
                  ? 'border-[#BD3A17] text-[#BD3A17] font-bold'
                  : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              Upload
            </Link>
            <Link
              to="/export"
              className={`h-full flex items-center px-1 border-b-2 transition-colors ${
                location.pathname === '/export'
                  ? 'border-[#BD3A17] text-[#BD3A17] font-bold'
                  : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              Export
            </Link>
            <Link
              to="/verify"
              className={`h-full flex items-center px-1 border-b-2 transition-colors ${
                location.pathname === '/verify'
                  ? 'border-[#BD3A17] text-[#BD3A17] font-bold'
                  : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              C1 Verification
            </Link>
          </nav>
        </div>

        {/* Right User info and Logout */}
        <div className="flex items-center space-x-6 text-xs">
          <div className="hidden sm:flex items-center space-x-2">
            <div className="w-7 h-7 rounded-full bg-[#E5E2DA] flex items-center justify-center font-bold text-[#44403C]">
              ER
            </div>
            <div className="text-left leading-tight">
              <div className="font-bold text-[#1C1917]">Elena Rostova</div>
              <div className="text-[10px] text-[#78716C]">elena@docflow.io</div>
            </div>
          </div>

          {mockActive && (
            <span className="hidden lg:inline-block px-2 py-0.5 bg-[#FEF3D6] text-[#B45309] border border-[#FDE68A] text-[10px] font-mono font-bold">
              MOCK MODE
            </span>
          )}

          <button
            onClick={() => logout()}
            className="flex items-center space-x-1 text-[#78716C] hover:text-[#1C1917] font-medium"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
