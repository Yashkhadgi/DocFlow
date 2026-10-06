import React from 'react';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'white' | 'slate';
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  color = 'primary',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-5 h-5 border-2',
    lg: 'w-7 h-7 border-3',
  };

  const colorClasses = {
    primary: 'border-indigo-600/20 border-t-indigo-600',
    white: 'border-white/30 border-t-white',
    slate: 'border-slate-300 border-t-slate-600',
  };

  return (
    <div
      role="status"
      aria-label="Loading"
      className={`inline-block rounded-full animate-spin ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};
