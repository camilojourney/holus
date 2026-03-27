import type { FreshnessStatus } from '@/lib/types';

interface Props {
  freshness: FreshnessStatus;
  modifiedAt?: string;
}

const styles: Record<FreshnessStatus, { dot: string; text: string }> = {
  fresh: { dot: 'var(--success)', text: 'var(--success)' },
  aging: { dot: 'var(--warning)', text: 'var(--warning)' },
  stale: { dot: 'var(--danger)', text: 'var(--danger)' },
};

export default function FreshnessIndicator({ freshness, modifiedAt }: Props) {
  const s = styles[freshness];
  const tooltip = modifiedAt
    ? `Last modified: ${new Date(modifiedAt).toLocaleString()}`
    : freshness;

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-medium"
      style={{ color: s.text }}
      title={tooltip}
    >
      <span className="status-dot" style={{ background: s.dot }} />
      {freshness}
    </span>
  );
}
