import React, { type ReactNode } from 'react';
import { Navbar } from './Navbar';
import { ToastProvider } from './Toast';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <ToastProvider>
      <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
        <Navbar />
        <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="bg-white border-t border-slate-200/80 py-6 text-center text-xs text-slate-500">
          DocFlow SaaS &bull; Person C &bull; Shared Design System (Tailwind v4)
        </footer>
      </div>
    </ToastProvider>
  );
};
