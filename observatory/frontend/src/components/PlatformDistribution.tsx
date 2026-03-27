'use client';

import { BarChart } from '@tremor/react';

interface Props {
  platformCounts: Record<string, number>;
}

export default function PlatformDistribution({ platformCounts }: Props) {
  const chartData = Object.entries(platformCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([platform, count]) => ({
      Platform: platform.replace(/_/g, '/'),
      Count: count,
    }));

  return (
    <div
      className="rounded-xl p-5"
      style={{
        border: '1px solid var(--border-default)',
        background: 'var(--surface-raised)',
      }}
    >
      <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
        Platform Distribution
      </h2>
      <BarChart
        className="h-48"
        data={chartData}
        index="Platform"
        categories={['Count']}
        colors={['amber']}
        showLegend={false}
        showGridLines={true}
        showYAxis={true}
        valueFormatter={(v: number) => String(v)}
        showAnimation={true}
      />
    </div>
  );
}
