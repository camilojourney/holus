import type { PlatformStats } from '@/lib/types';

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  name: string;
  stats: PlatformStats;
}

export default function PlatformCard({ name, stats }: Props) {
  const growth = stats.followers_30d_ago > 0
    ? ((stats.followers - stats.followers_30d_ago) / stats.followers_30d_ago * 100).toFixed(1)
    : '0';
  const isPositive = Number(growth) > 0;

  return (
    <div
      className="rounded-xl p-4"
      style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--border-default)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-sm font-semibold capitalize"
          style={{ color: 'var(--brand)' }}
        >
          {name}
        </span>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full"
          style={{
            background: isPositive ? 'var(--success-subtle)' : 'var(--danger-subtle)',
            color: isPositive ? 'var(--success)' : 'var(--danger)',
          }}
        >
          {isPositive ? '+' : ''}{growth}%
        </span>
      </div>
      <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        {fmt(stats.followers)}
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>followers</p>
      <div
        className="mt-3 pt-3 grid grid-cols-2 gap-2 text-xs"
        style={{ borderTop: '1px solid var(--border-subtle)' }}
      >
        <div>
          <span style={{ color: 'var(--text-tertiary)' }}>Posts</span>
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{stats.posts_30d}</p>
        </div>
        <div>
          <span style={{ color: 'var(--text-tertiary)' }}>Impr.</span>
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(stats.impressions_30d)}</p>
        </div>
        <div>
          <span style={{ color: 'var(--text-tertiary)' }}>Eng. rate</span>
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{(stats.engagement_rate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <span style={{ color: 'var(--text-tertiary)' }}>Top type</span>
          <p className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>{stats.top_content_type}</p>
        </div>
      </div>
    </div>
  );
}
