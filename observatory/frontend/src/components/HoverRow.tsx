'use client';

import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function HoverRow({ children, className, style }: Props) {
  return (
    <div
      className={`transition-colors ${className ?? ''}`}
      style={style}
      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-2)')}
      onMouseLeave={(e) => (e.currentTarget.style.background = '')}
    >
      {children}
    </div>
  );
}
