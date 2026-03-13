import type { PillarStats, ProductStats } from '@/lib/types';

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

const pillarColors: Record<string, string> = {
  authority: 'bg-indigo-500',
  tutorial: 'bg-blue-500',
  entertainment: 'bg-amber-500',
  conversion: 'bg-green-500',
};

const productColors: Record<string, string> = {
  pilaster: 'bg-purple-500',
  genpeli: 'bg-rose-500',
  invoz: 'bg-cyan-500',
  holus: 'bg-indigo-500',
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
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
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
                    <span className="capitalize text-gray-700 dark:text-gray-300 font-medium">{name}</span>
                    <span className="text-xs text-gray-400 dark:text-gray-600">
                      {stats.count} posts · {fmt(stats.total_impressions)} impr · {(stats.avg_engagement_rate * 100).toFixed(1)}% eng
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${pillarColors[name] ?? 'bg-gray-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* By Product */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
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
                    <span className="capitalize text-gray-700 dark:text-gray-300 font-medium">{name}</span>
                    <span className="text-xs text-gray-400 dark:text-gray-600">
                      {stats.count} posts · {fmt(stats.total_impressions)} impr · {(stats.avg_engagement_rate * 100).toFixed(1)}% eng
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${productColors[name] ?? 'bg-gray-500'}`}
                      style={{ width: `${pct}%` }}
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
