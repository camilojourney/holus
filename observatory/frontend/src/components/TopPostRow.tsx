import type { TopPost } from '@/lib/types';

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  post: TopPost;
}

export default function TopPostRow({ post }: Props) {
  const date = new Date(post.published_at);
  const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;

  return (
    <div className="px-5 py-3.5 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
          {post.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded capitalize"
            style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
          >
            {post.platform}
          </span>
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded capitalize"
            style={{ background: 'var(--brand-subtle)', color: 'var(--brand)' }}
          >
            {post.product}
          </span>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{dateStr}</span>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs shrink-0" style={{ color: 'var(--text-secondary)' }}>
        <div className="text-right">
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(post.impressions)}</p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>views</p>
        </div>
        <div className="text-right">
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(post.likes)}</p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>likes</p>
        </div>
        <div className="text-right">
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(post.shares)}</p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>shares</p>
        </div>
        <div className="text-right w-12">
          <p
            className="font-semibold"
            style={{
              color: post.engagement_rate >= 0.07
                ? 'var(--success)'
                : post.engagement_rate >= 0.04
                ? 'var(--warning)'
                : 'var(--text-secondary)',
            }}
          >
            {(post.engagement_rate * 100).toFixed(1)}%
          </p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>eng.</p>
        </div>
      </div>
    </div>
  );
}
