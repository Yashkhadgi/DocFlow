import React from 'react';
import type { DocumentStatus } from '../api/types';

export interface StatusBadgeProps {
  status: DocumentStatus | 'needs_review' | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const normStatus = (status || '').toLowerCase();

  const config: Record<string, { label: string; style: string }> = {
    queued: {
      label: 'QUEUED',
      style: 'bg-[#F0F0F0] text-[#555555] border-[#CCCCCC]',
    },
    processing: {
      label: 'PROCESSING',
      style: 'bg-[#E8F0FE] text-[#1A73E8] border-[#AECBFA]',
    },
    needs_review: {
      label: 'NEEDS REVIEW',
      style: 'bg-[#FEF3D6] text-[#B45309] border-[#FDE68A]',
    },
    approved: {
      label: 'APPROVED',
      style: 'bg-[#E6F4EA] text-[#137333] border-[#CEEAD6]',
    },
    failed: {
      label: 'FAILED',
      style: 'bg-[#FCE8E6] text-[#C5221F] border-[#FAD2CF]',
    },
    duplicate: {
      label: 'DUPLICATE',
      style: 'bg-[#F3E8FF] text-[#7E22CE] border-[#E9D5FF]',
    },
    unsupported_type: {
      label: 'UNSUPPORTED TYPE',
      style: 'bg-[#FCE8E6] text-[#C5221F] border-[#FAD2CF]',
    },
    file_too_large: {
      label: 'FILE TOO LARGE',
      style: 'bg-[#FCE8E6] text-[#C5221F] border-[#FAD2CF]',
    },
    uploading: {
      label: 'UPLOADING',
      style: 'bg-[#E8F0FE] text-[#1A73E8] border-[#AECBFA]',
    },
  };

  const current = config[normStatus] || {
    label: (status || 'UNKNOWN').toUpperCase().replace('_', ' '),
    style: 'bg-[#F0F0F0] text-[#555555] border-[#CCCCCC]',
  };

  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2 py-0.5 text-[11px]',
  };

  return (
    <span
      className={`
        inline-flex items-center justify-center font-extrabold uppercase tracking-wider border rounded-none shrink-0 font-sans select-none
        ${current.style}
        ${sizeStyles[size]}
        ${className}
      `}
    >
      {current.label}
    </span>
  );
};
