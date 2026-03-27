'use client';

import { useRef, useCallback, type KeyboardEvent, type ReactNode } from 'react';

interface RadioGroupProps<T extends string> {
  label: string;
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  renderLabel?: (option: T) => ReactNode;
  className?: string;
}

/**
 * Accessible radio group with arrow key navigation per WAI-ARIA radio group pattern.
 * Left/Up selects previous option, Right/Down selects next option.
 * Home selects first, End selects last.
 */
export default function RadioGroup<T extends string>({
  label,
  options,
  value,
  onChange,
  renderLabel,
  className = '',
}: RadioGroupProps<T>) {
  const groupRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      const currentIdx = options.indexOf(value);
      let nextIdx = -1;

      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          nextIdx = (currentIdx + 1) % options.length;
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          nextIdx = (currentIdx - 1 + options.length) % options.length;
          break;
        case 'Home':
          nextIdx = 0;
          break;
        case 'End':
          nextIdx = options.length - 1;
          break;
        default:
          return;
      }

      e.preventDefault();
      onChange(options[nextIdx]);

      // Move focus to the newly selected radio
      const buttons = groupRef.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]');
      buttons?.[nextIdx]?.focus();
    },
    [options, value, onChange],
  );

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={label}
      className={`flex items-center gap-1.5 rounded-lg p-1 ${className}`}
      style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--border-default)',
      }}
      onKeyDown={handleKeyDown}
    >
      {options.map((option) => {
        const isSelected = value === option;
        return (
          <button
            key={option}
            role="radio"
            aria-checked={isSelected}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onChange(option)}
            className="px-3 py-2 rounded-md text-xs font-medium capitalize transition-colors focus-ring"
            style={{
              background: isSelected ? 'var(--brand)' : 'transparent',
              color: isSelected ? 'var(--text-inverse)' : 'var(--text-secondary)',
            }}
          >
            {renderLabel ? renderLabel(option) : option}
          </button>
        );
      })}
    </div>
  );
}
