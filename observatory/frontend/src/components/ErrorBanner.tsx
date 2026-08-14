import { AlertCircle } from 'lucide-react';
import { isPublicOrDemoSurface } from '@/lib/connection';

interface Props {
  message?: string;
}

export default function ErrorBanner({ message }: Props) {
  const publicSurface = isPublicOrDemoSurface();

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
          {publicSurface ? 'Connection required' : 'Service unavailable'}
        </p>
        {message && (
          <p className="text-xs mt-0.5" style={{ color: 'var(--danger)', opacity: 0.8 }}>{message}</p>
        )}
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          {publicSurface
            ? 'Live Observatory data requires an authenticated backend connection. Localhost is not used from this public demo.'
            : 'Check that the Observatory API is reachable for this local development session.'}
        </p>
      </div>
    </div>
  );
}
