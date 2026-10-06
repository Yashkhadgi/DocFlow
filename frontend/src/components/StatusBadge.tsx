import React from 'react';
import type { DocumentStatus } from '../api/types';

export interface StatusBadgeProps {
  status: DocumentStatus;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const config: Record<
    DocumentStatus,
    { label: string; container: string; dot?: string; animateDot?: boolean }
  > = {
    queued: {
      label: 'Queued',
      container: 'bg-slate-100 text-slate-700 border-slate-200',
      dot: 'bg-slate-400',
    },
    processing: {
      label: 'Processing',
      container: 'bg-blue-50 text-blue-700 border-blue-200',
      dot: 'bg-blue-500',
      animateDot: true,
    },
    needs_review: {
      label: 'Needs Review',
      container: 'bg-amber-50 text-amber-700 border-amber-200',
      dot: 'bg-amber-500',
    },
    approved: {
      label: 'Approved',
      container: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      dot: 'bg-emerald-500',
    },
    failed: {
      label: 'Failed',
      container: 'bg-rose-50 text-rose-700 border-rose-200',
      dot: 'bg-rose-500',
    },
    duplicate: {
      label: 'Duplicate',
      container: 'bg-purple-50 text-purple-700 border-purple-200',
      dot: 'bg-purple-500',
    },
  };

  const current = config[status] || config.queued;

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 font-semibold rounded-full border shrink-0
        ${current.container}
        ${sizeStyles[size]}
        ${className}
      `}
    >
      <span className="relative flex h-2 w-2">
        {current.animateDot && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
        )}
        <span
          className={`relative inline-flex rounded-full h-2 w-2 ${
            current.dot || 'bg-slate-400'
          }`}
        />
      </span>
      <span>{current.label}</span>
    </span>
  );
};
