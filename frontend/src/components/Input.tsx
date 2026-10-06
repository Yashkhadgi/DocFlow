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
      <div className={`${fullWidth ? 'w-full' : ''} space-y-1.5`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-semibold text-slate-700 select-none"
          >
            {label}
          </label>
        )}
        <div className="relative rounded-lg shadow-xs">
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
              block w-full rounded-lg border text-sm text-slate-900 placeholder-slate-400 bg-white
              transition-colors duration-150 ease-in-out
              focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600
              disabled:bg-slate-50 disabled:text-slate-500 disabled:cursor-not-allowed
              ${startIcon ? 'pl-9' : 'pl-3'}
              ${endIcon ? 'pr-9' : 'pr-3'}
              ${pyPaddingStyle(props.size)}
              ${
                error
                  ? 'border-rose-500 text-rose-900 focus:border-rose-500 focus:ring-rose-500/20'
                  : 'border-slate-300'
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

        {error && <p className="text-xs font-medium text-rose-600 mt-1">{error}</p>}
        {!error && helperText && (
          <p className="text-xs text-slate-500 mt-1">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

function pyPaddingStyle(_size?: any): string {
  return 'py-2';
}
