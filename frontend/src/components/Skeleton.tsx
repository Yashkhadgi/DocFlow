import React from 'react';

export interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'card';
  width?: string | number;
  height?: string | number;
  className?: string;
  count?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className = '',
  count = 1,
}) => {
  const baseClasses = 'bg-slate-200/80 animate-pulse shrink-0';

  const variantClasses = {
    text: 'h-4 rounded-md w-full',
    circular: 'rounded-full',
    rectangular: 'rounded-lg w-full',
    card: 'rounded-xl border border-slate-200 p-6 h-32 w-full',
  };

  const style: React.CSSProperties = {
    width: width !== undefined ? width : undefined,
    height: height !== undefined ? height : undefined,
  };

  const items = Array.from({ length: count });

  if (variant === 'card') {
    return (
      <div className="space-y-3">
        {items.map((_, i) => (
          <div
            key={i}
            className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4 animate-pulse"
          >
            <div className="flex items-center justify-between">
              <div className="h-5 bg-slate-200 rounded-md w-1/3" />
              <div className="h-6 bg-slate-200 rounded-full w-20" />
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-slate-200 rounded-md w-3/4" />
              <div className="h-4 bg-slate-200 rounded-md w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {items.map((_, i) => (
        <div
          key={i}
          className={`${baseClasses} ${variantClasses[variant]} ${className}`}
          style={style}
        />
      ))}
    </>
  );
};
