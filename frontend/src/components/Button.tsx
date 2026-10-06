import React, { type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Spinner } from './Spinner';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
  children: ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  disabled,
  children,
  className = '',
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-none transition-all focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed select-none border font-sans';

  const variantStyles = {
    primary:
      'bg-[#BD3A17] hover:bg-[#A33113] text-white border-transparent font-semibold shadow-xs',
    secondary:
      'bg-white hover:bg-[#F5F2EB] text-[#222222] border-[#D5D1C8]',
    danger:
      'bg-[#C5221F] hover:bg-[#A81C19] text-white border-transparent font-semibold',
    outline:
      'bg-white hover:bg-[#F5F2EB] text-[#444444] border-[#D5D1C8]',
    ghost:
      'bg-transparent hover:bg-[#F5F2EB] text-[#555555] border-transparent',
  };

  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-sm font-semibold gap-2',
  };

  const spinnerColors = {
    primary: 'white',
    secondary: 'slate',
    danger: 'white',
    outline: 'slate',
    ghost: 'slate',
  } as const;

  return (
    <button
      disabled={disabled || isLoading}
      className={`
        ${baseStyles}
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...props}
    >
      {isLoading ? (
        <>
          <Spinner size={size === 'lg' ? 'md' : 'sm'} color={spinnerColors[variant]} />
          <span>Processing...</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  );
};
