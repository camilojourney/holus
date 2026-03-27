import { AlertCircle } from 'lucide-react';

interface Props {
  message?: string;
}

export default function ErrorBanner({ message }: Props) {
  return (
    <div
      role="alert"
      className="rounded-xl px-5 py-4 flex items-start gap-3"
      style={{
        background: 'var(--danger-subtle)',
        border: '1px solid var(--danger)',
        borderLeftWidth: '3px',
      }}
    >
      <AlertCircle size={18} style={{ color: 'var(--danger)', marginTop: 1, flexShrink: 0 }} aria-hidden="true" />
      <div>
        <p className="text-sm font-medium" style={{ color: 'var(--danger)' }}>
          Service unavailable
        </p>
        {message && (
          <p className="text-xs mt-0.5" style={{ color: 'var(--danger)', opacity: 0.8 }}>{message}</p>
        )}
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Check that the Observatory API is running at{' '}
          {process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001'}
        </p>
      </div>
    </div>
  );
}
