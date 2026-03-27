import type { PillarStats, ProductStats } from '@/lib/types';

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

const pillarColors: Record<string, string> = {
  authority: 'var(--brand-primary, #F59E0B)',
  tutorial: 'var(--info, #F59E0B)',
  entertainment: 'var(--warning, #fbbf24)',
  conversion: 'var(--success, #34d399)',
};

const productColors: Record<string, string> = {
  pilaster: 'var(--brand-accent, #FBBF24)',
  genpeli: 'var(--danger, #f87171)',
  invoz: '#06B6D4',
  holus: 'var(--brand-primary, #F59E0B)',
};

interface Props {
  byPillar: Record<string, PillarStats>;
  byProduct: Record<string, ProductStats>;
}

export default function PillarBreakdown({ byPillar, byProduct }: Props) {
  const totalPillarImpr = Object.values(byPillar).reduce((s, p) => s + p.total_impressions, 0) || 1;
  const totalProductImpr = Object.values(byProduct).reduce((s, p) => s + p.total_impressions, 0) || 1;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* By Pillar */}
      <div
        className="rounded-xl p-5"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <h2
          className="text-sm font-semibold mb-4"
          style={{ color: 'var(--text-primary)' }}
        >
          Content by Pillar
        </h2>
        <div className="space-y-3">
          {Object.entries(byPillar)
            .sort((a, b) => b[1].total_impressions - a[1].total_impressions)
            .map(([name, stats]) => {
              const pct = (stats.total_impressions / totalPillarImpr * 100).toFixed(0);
              return (
                <div key={name}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="capitalize font-medium" style={{ color: 'var(--text-primary)' }}>{name}</span>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {stats.count} posts · {fmt(stats.total_impressions)} impr · {(stats.avg_engagement_rate * 100).toFixed(1)}% eng
                    </span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--surface-2)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        background: pillarColors[name] ?? 'var(--text-tertiary)',
                      }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* By Product */}
      <div
        className="rounded-xl p-5"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <h2
          className="text-sm font-semibold mb-4"
          style={{ color: 'var(--text-primary)' }}
        >
          Content by Product
        </h2>
        <div className="space-y-3">
          {Object.entries(byProduct)
            .sort((a, b) => b[1].total_impressions - a[1].total_impressions)
            .map(([name, stats]) => {
              const pct = (stats.total_impressions / totalProductImpr * 100).toFixed(0);
              return (
                <div key={name}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="capitalize font-medium" style={{ color: 'var(--text-primary)' }}>{name}</span>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {stats.count} posts · {fmt(stats.total_impressions)} impr · {(stats.avg_engagement_rate * 100).toFixed(1)}% eng
                    </span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--surface-2)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        background: productColors[name] ?? 'var(--text-tertiary)',
                      }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
