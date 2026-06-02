'use client';

import React from 'react';
import { SearchIcon } from '@/components/icons/Icons';

interface SmallSearchInputProps {
  value: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
}

const SmallSearchInput = React.forwardRef<HTMLInputElement, SmallSearchInputProps>(
  function SmallSearchInput({ value, onChange, placeholder = '' }, ref) {
    return (
      <div className="relative w-full max-w-xs">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          aria-label={placeholder}
          className="w-full h-9 pl-9 pr-20 rounded-full border border-border bg-background text-sm text-text-primary placeholder:text-text-muted outline-none transition focus:border-primary-blue focus:ring-2 focus:ring-primary-blue/20"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1">
          <kbd className="px-1.5 py-0.5 text-[10px] text-text-muted bg-background border border-card-border rounded">Ctrl</kbd>
          <kbd className="px-1.5 py-0.5 text-[10px] text-text-muted bg-background border border-card-border rounded">Shift</kbd>
          <kbd className="px-1.5 py-0.5 text-[10px] text-text-muted bg-background border border-card-border rounded">K</kbd>
        </div>
      </div>
    );
  }
);

SmallSearchInput.displayName = 'SmallSearchInput';

export default SmallSearchInput;
