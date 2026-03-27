'use client';

import { useState, useMemo } from 'react';
import { AreaChart } from '@tremor/react';
import { generateEngagementData, type EngagementDataPoint } from '@/lib/demo-data';
import RadioGroup from '@/components/RadioGroup';

const PLATFORMS = ['all', 'linkedin', 'instagram', 'twitter', 'threads', 'tiktok'] as const;
type Platform = typeof PLATFORMS[number];

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function EngagementPage() {
  const [platform, setPlatform] = useState<Platform>('all');
  const [metric, setMetric] = useState<'impressions' | 'likes' | 'comments' | 'shares' | 'engagement_rate'>('impressions');

  const rawData = useMemo(() => generateEngagementData(), []);

  const filtered = useMemo(() => {
    if (platform === 'all') return rawData;
    return rawData.filter((d) => d.platform === platform);
  }, [rawData, platform]);

  const dailyAgg = useMemo(() => {
    const byDate: Record<string, EngagementDataPoint> = {};
    for (const d of filtered) {
      if (!byDate[d.date]) {
        byDate[d.date] = { ...d };
      } else {
        byDate[d.date].impressions += d.impressions;
        byDate[d.date].likes += d.likes;
        byDate[d.date].comments += d.comments;
        byDate[d.date].shares += d.shares;
        byDate[d.date].posts += d.posts;
      }
    }
    return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
  }, [filtered]);

  const platformSummary = useMemo(() => {
    const summary: Record<string, { impressions: number; likes: number; comments: number; shares: number; posts: number; days: number }> = {};
    for (const d of rawData) {
      if (!summary[d.platform]) {
        summary[d.platform] = { impressions: 0, likes: 0, comments: 0, shares: 0, posts: 0, days: 0 };
      }
      summary[d.platform].impressions += d.impressions;
      summary[d.platform].likes += d.likes;
      summary[d.platform].comments += d.comments;
      summary[d.platform].shares += d.shares;
      summary[d.platform].posts += d.posts;
      summary[d.platform].days += 1;
    }
    return summary;
  }, [rawData]);

  const totals = useMemo(() => ({
    impressions: dailyAgg.reduce((s, d) => s + d.impressions, 0),
    likes: dailyAgg.reduce((s, d) => s + d.likes, 0),
    comments: dailyAgg.reduce((s, d) => s + d.comments, 0),
    shares: dailyAgg.reduce((s, d) => s + d.shares, 0),
    posts: dailyAgg.reduce((s, d) => s + d.posts, 0),
  }), [dailyAgg]);

  const totalEngagement = totals.likes + totals.comments + totals.shares;
  const avgEngRate = totals.impressions > 0 ? (totalEngagement / totals.impressions * 100).toFixed(1) : '0';

  const chartData = dailyAgg.map((d) => {
    const eng = d.likes + d.comments + d.shares;
    return {
      date: d.date.slice(5),
      Value: metric === 'engagement_rate'
        ? (d.impressions > 0 ? eng / d.impressions : 0)
        : d[metric],
    };
  });

  return (
    <div style={{ padding: 'var(--page-padding)' }} className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Engagement Signals
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Audience interaction signals -- impressions, reactions, and engagement rate by channel (30d)
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <RadioGroup
          label="Filter by platform"
          options={PLATFORMS}
          value={platform}
          onChange={setPlatform}
        />
        <RadioGroup
          label="Filter by metric"
          options={['impressions', 'likes', 'comments', 'shares', 'engagement_rate'] as const}
          value={metric}
          onChange={setMetric}
          renderLabel={(m) => m === 'engagement_rate' ? 'Eng. Rate' : m}
        />
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Impressions', value: fmt(totals.impressions) },
          { label: 'Likes', value: fmt(totals.likes) },
          { label: 'Comments', value: fmt(totals.comments) },
          { label: 'Shares', value: fmt(totals.shares) },
          { label: 'Avg Eng. Rate', value: `${avgEngRate}%` },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{
              background: 'var(--surface-raised)',
              border: '1px solid var(--border-default)',
            }}
          >
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
            <p className="text-xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Chart — Recharts AreaChart */}
      <div
        className="rounded-xl p-5"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold capitalize" style={{ color: 'var(--text-primary)' }}>
            {metric === 'engagement_rate' ? 'Engagement Rate' : metric} over 30 days
            {platform !== 'all' ? ` (${platform})` : ''}
          </h2>
        </div>
        <AreaChart
          className="h-40"
          data={chartData}
          index="date"
          categories={['Value']}
          colors={['amber']}
          curveType="natural"
          showXAxis={true}
          showYAxis={true}
          showGridLines={true}
          showLegend={false}
          autoMinValue={true}
          valueFormatter={(v: number) =>
            metric === 'engagement_rate' ? `${(v * 100).toFixed(1)}%` : fmt(v)
          }
          showAnimation={true}
        />
      </div>

      {/* Platform breakdown table */}
      <div
        className="rounded-xl"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Platform Breakdown (30d)
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {['Platform', 'Impressions', 'Likes', 'Comments', 'Shares', 'Posts', 'Eng. Rate'].map((h, i) => (
                  <th
                    key={h}
                    scope="col"
                    className={`${i === 0 ? 'text-left px-5' : 'text-right px-4'} py-3 text-xs font-medium`}
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(platformSummary)
                .sort(([, a], [, b]) => b.impressions - a.impressions)
                .map(([name, s]) => {
                  const eng = s.likes + s.comments + s.shares;
                  const engRate = s.impressions > 0 ? (eng / s.impressions * 100).toFixed(1) : '0';
                  return (
                    <tr key={name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td className="px-5 py-3">
                        <span
                          className="text-xs font-medium px-2 py-0.5 rounded capitalize"
                          style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
                        >
                          {name}
                        </span>
                      </td>
                      <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(s.impressions)}</td>
                      <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(s.likes)}</td>
                      <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(s.comments)}</td>
                      <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(s.shares)}</td>
                      <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{s.posts}</td>
                      <td className="text-right px-5 py-3">
                        <span
                          className="font-semibold"
                          style={{
                            color: Number(engRate) >= 7 ? 'var(--success)' : Number(engRate) >= 4 ? 'var(--warning)' : 'var(--text-secondary)',
                          }}
                        >
                          {engRate}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
