'use client';

import { AreaChart } from '@tremor/react';
import type { DailyGrowth } from '@/lib/types';

interface Props {
  data: DailyGrowth[];
}

export default function GrowthChart({ data }: Props) {
  if (data.length < 2) return null;

  const followers = data.map((d) => d.total_followers);
  const min = Math.min(...followers);
  const max = Math.max(...followers);

  const chartData = data.map((d) => ({
    date: d.date.slice(5), // "MM-DD"
    Followers: d.total_followers,
  }));

  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--border-default)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h2
          className="text-sm font-semibold"
          style={{ color: 'var(--text-primary)' }}
        >
          Follower Growth (30d)
        </h2>
        <div
          className="flex items-center gap-3 text-xs"
          style={{ color: 'var(--text-tertiary)' }}
        >
          <span>{min.toLocaleString()}</span>
          <span style={{ color: 'var(--border-strong)' }}>&rarr;</span>
          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
            {max.toLocaleString()}
          </span>
        </div>
      </div>
      <AreaChart
        className="h-40"
        data={chartData}
        index="date"
        categories={['Followers']}
        colors={['amber']}
        curveType="natural"
        showXAxis={true}
        showYAxis={true}
        showGridLines={true}
        showLegend={false}
        autoMinValue={true}
        valueFormatter={(v: number) => v.toLocaleString()}
        showAnimation={true}
      />
    </div>
  );
}
