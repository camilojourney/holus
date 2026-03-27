'use client';

import { useState, useMemo } from 'react';
import { generateEngagementData, type EngagementDataPoint } from '@/lib/demo-data';
import RadioGroup from '@/components/RadioGroup';

const PLATFORMS = ['all', 'linkedin', 'instagram', 'twitter', 'threads', 'tiktok'] as const;
type Platform = typeof PLATFORMS[number];

const platformColors: Record<string, { light: string; dark: string }> = {
  linkedin: { light: '#2563eb', dark: '#60a5fa' },
  instagram: { light: '#ec4899', dark: '#f472b6' },
  twitter: { light: '#0ea5e9', dark: '#38bdf8' },
  threads: { light: '#6b7280', dark: '#9ca3af' },
  tiktok: { light: '#111827', dark: '#e5e7eb' },
};

function getPlatformColor(platform: string): string {
  const colors = platformColors[platform];
  if (!colors) return '#6366f1';
  if (typeof window !== 'undefined' && document.documentElement.classList.contains('dark')) {
    return colors.dark;
  }
  return colors.light;
}

const platformBadgeClass: Record<string, string> = {
  linkedin: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
  instagram: 'bg-pink-50 text-pink-700 dark:bg-pink-950 dark:text-pink-400',
  twitter: 'bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-400',
  threads: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  tiktok: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function MiniChart({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 200;
  const h = 48;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-12" aria-label="Engagement sparkline">
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export default function EngagementPage() {
  const [platform, setPlatform] = useState<Platform>('all');
  const [metric, setMetric] = useState<'impressions' | 'likes' | 'comments' | 'shares' | 'engagement_rate'>('impressions');

  const rawData = useMemo(() => generateEngagementData(), []);

  const filtered = useMemo(() => {
    if (platform === 'all') return rawData;
    return rawData.filter((d) => d.platform === platform);
  }, [rawData, platform]);

  // Aggregate by date for the chart
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

  // Platform-level summary
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

  // Chart data
  const chartValues = dailyAgg.map((d) => {
    if (metric === 'engagement_rate') {
      const eng = d.likes + d.comments + d.shares;
      return d.impressions > 0 ? eng / d.impressions : 0;
    }
    return d[metric];
  });

  const chartColor = platform === 'all' ? '#6366f1' : getPlatformColor(platform);

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Engagement Tracker</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Likes, comments, shares, and impressions across platforms (30 days)
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
          { label: 'Impressions', value: fmt(totals.impressions), color: 'blue' },
          { label: 'Likes', value: fmt(totals.likes), color: 'pink' },
          { label: 'Comments', value: fmt(totals.comments), color: 'yellow' },
          { label: 'Shares', value: fmt(totals.shares), color: 'green' },
          { label: 'Avg Eng. Rate', value: `${avgEngRate}%`, color: Number(avgEngRate) >= 5 ? 'green' : 'yellow' },
        ].map(({ label, value }) => (
          <div key={label} className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
            <p className="text-xs text-gray-400 dark:text-gray-400">{label}</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 capitalize">
            {metric === 'engagement_rate' ? 'Engagement Rate' : metric} over 30 days
            {platform !== 'all' ? ` (${platform})` : ''}
          </h2>
        </div>
        <MiniChart data={chartValues} color={chartColor} />
        <div className="flex justify-between mt-2 text-xs text-gray-400 dark:text-gray-400">
          <span>{dailyAgg[0]?.date.slice(5)}</span>
          <span>{dailyAgg[dailyAgg.length - 1]?.date.slice(5)}</span>
        </div>
      </div>

      {/* Platform breakdown table */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Platform Breakdown (30d)
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
                <th scope="col" className="text-left px-5 py-3 font-medium">Platform</th>
                <th scope="col" className="text-right px-4 py-3 font-medium">Impressions</th>
                <th scope="col" className="text-right px-4 py-3 font-medium">Likes</th>
                <th scope="col" className="text-right px-4 py-3 font-medium">Comments</th>
                <th scope="col" className="text-right px-4 py-3 font-medium">Shares</th>
                <th scope="col" className="text-right px-4 py-3 font-medium">Posts</th>
                <th scope="col" className="text-right px-5 py-3 font-medium">Eng. Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(platformSummary)
                .sort(([, a], [, b]) => b.impressions - a.impressions)
                .map(([name, s]) => {
                  const eng = s.likes + s.comments + s.shares;
                  const engRate = s.impressions > 0 ? (eng / s.impressions * 100).toFixed(1) : '0';
                  return (
                    <tr key={name} className="border-b border-gray-50 dark:border-gray-900 last:border-0">
                      <td className="px-5 py-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${platformBadgeClass[name] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}`}>
                          {name}
                        </span>
                      </td>
                      <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmt(s.impressions)}</td>
                      <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmt(s.likes)}</td>
                      <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmt(s.comments)}</td>
                      <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmt(s.shares)}</td>
                      <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{s.posts}</td>
                      <td className="text-right px-5 py-3">
                        <span className={`font-semibold ${Number(engRate) >= 7 ? 'text-green-600 dark:text-green-400' : Number(engRate) >= 4 ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-600 dark:text-gray-400'}`}>
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
