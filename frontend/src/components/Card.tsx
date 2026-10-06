import React, { type ReactNode } from 'react';

export interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  hoverable = false,
}) => {
  return (
    <div
      onClick={onClick}
      className={`
        bg-white border border-[#E5E2DA] rounded-none shadow-xs transition-all duration-150
        ${hoverable ? 'hover:border-[#C5C1B5] cursor-pointer' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
};

export interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className = '' }) => {
  return <div className={`p-6 border-b border-[#F0ECE1] ${className}`}>{children}</div>;
};

export interface CardTitleProps {
  children: ReactNode;
  className?: string;
}

export const CardTitle: React.FC<CardTitleProps> = ({ children, className = '' }) => {
  return <h3 className={`text-lg font-bold text-[#1C1917] font-serif-title ${className}`}>{children}</h3>;
};

export interface CardDescriptionProps {
  children: ReactNode;
  className?: string;
}

export const CardDescription: React.FC<CardDescriptionProps> = ({ children, className = '' }) => {
  return <p className={`text-xs text-[#78716C] mt-1 font-sans ${className}`}>{children}</p>;
};

export interface CardContentProps {
  children: ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({ children, className = '' }) => {
  return <div className={`p-6 ${className}`}>{children}</div>;
};

export interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className = '' }) => {
  return <div className={`px-6 py-4 bg-[#FBF9F5] border-t border-[#F0ECE1] rounded-none flex items-center justify-between ${className}`}>{children}</div>;
};
