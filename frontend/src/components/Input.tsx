import { forwardRef } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  startIcon?: ReactNode;
  endIcon?: ReactNode;
  fullWidth?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      startIcon,
      endIcon,
      fullWidth = true,
      className = '',
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className={`${fullWidth ? 'w-full' : ''} space-y-1`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-semibold text-[#44403C] uppercase tracking-wider select-none font-sans"
          >
            {label}
          </label>
        )}
        <div className="relative rounded-none">
          {startIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              {startIcon}
            </div>
          )}

          <input
            id={inputId}
            ref={ref}
            disabled={disabled}
            className={`
              block w-full rounded-none border text-sm text-[#1C1917] placeholder-[#A8A29E] bg-white
              transition-colors duration-150 ease-in-out py-2.5 px-3 font-sans
              focus:outline-none focus:border-[#BD3A17] focus:ring-1 focus:ring-[#BD3A17]
              disabled:bg-[#F5F2EB] disabled:text-[#78716C] disabled:cursor-not-allowed
              ${startIcon ? 'pl-9' : ''}
              ${endIcon ? 'pr-9' : ''}
              ${
                error
                  ? 'border-[#C5221F] text-[#C5221F] focus:border-[#C5221F] focus:ring-[#C5221F]'
                  : 'border-[#D5D1C8]'
              }
              ${className}
            `}
            {...props}
          />

          {endIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400">
              {endIcon}
            </div>
          )}
        </div>

        {error && <p className="text-xs font-medium text-[#C5221F] mt-1">{error}</p>}
        {!error && helperText && (
          <p className="text-xs text-[#78716C] mt-1">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
