'use client';

import { useState, useMemo } from 'react';
import { generateFollowerData, type FollowerDataPoint } from '@/lib/demo-data';

const PLATFORMS = ['all', 'linkedin', 'instagram', 'twitter', 'threads', 'tiktok'] as const;
type Platform = typeof PLATFORMS[number];

const platformColors: Record<string, string> = {
  linkedin: '#2563eb',
  instagram: '#ec4899',
  twitter: '#0ea5e9',
  threads: '#6b7280',
  tiktok: '#111827',
};

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

function GrowthLine({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 800;
  const h = 140;
  const padding = { top: 8, right: 8, bottom: 4, left: 8 };
  const chartW = w - padding.left - padding.right;
  const chartH = h - padding.top - padding.bottom;

  const points = data.map((v, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartW;
    const y = padding.top + chartH - ((v - min) / range) * chartH;
    return { x, y };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto" aria-label="Follower growth chart">
      <defs>
        <linearGradient id={`fill-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.15" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#fill-${color.replace('#', '')})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export default function FollowersPage() {
  const [platform, setPlatform] = useState<Platform>('all');

  const rawData = useMemo(() => generateFollowerData(), []);

  const filtered = useMemo(() => {
    if (platform === 'all') return rawData;
    return rawData.filter((d) => d.platform === platform);
  }, [rawData, platform]);

  // Aggregate followers by date (sum all platforms for "all" view)
  const dailyFollowers = useMemo(() => {
    const byDate: Record<string, { followers: number; new_followers: number; unfollows: number; net_change: number }> = {};
    for (const d of filtered) {
      if (!byDate[d.date]) {
        byDate[d.date] = { followers: 0, new_followers: 0, unfollows: 0, net_change: 0 };
      }
      byDate[d.date].followers += d.followers;
      byDate[d.date].new_followers += d.new_followers;
      byDate[d.date].unfollows += d.unfollows;
      byDate[d.date].net_change += d.net_change;
    }
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, v]) => ({ date, ...v }));
  }, [filtered]);

  // Per-platform summary
  const platformSummary = useMemo(() => {
    const platforms = ['linkedin', 'instagram', 'twitter', 'threads', 'tiktok'];
    return platforms.map((p) => {
      const pData = rawData.filter((d) => d.platform === p);
      const first = pData[0];
      const last = pData[pData.length - 1];
      const totalNew = pData.reduce((s, d) => s + d.new_followers, 0);
      const totalUnfollows = pData.reduce((s, d) => s + d.unfollows, 0);
      const growth = first && last && first.followers > 0
        ? ((last.followers - first.followers) / first.followers * 100).toFixed(1)
        : '0';
      return {
        platform: p,
        current: last?.followers ?? 0,
        start: first?.followers ?? 0,
        new_followers: totalNew,
        unfollows: totalUnfollows,
        net_change: totalNew - totalUnfollows,
        growth_pct: growth,
      };
    });
  }, [rawData]);

  const currentTotal = dailyFollowers.length > 0 ? dailyFollowers[dailyFollowers.length - 1].followers : 0;
  const startTotal = dailyFollowers.length > 0 ? dailyFollowers[0].followers : 0;
  const totalNetChange = currentTotal - startTotal;
  const totalGrowthPct = startTotal > 0 ? ((totalNetChange / startTotal) * 100).toFixed(1) : '0';
  const totalNewFollowers = dailyFollowers.reduce((s, d) => s + d.new_followers, 0);
  const totalUnfollows = dailyFollowers.reduce((s, d) => s + d.unfollows, 0);

  const chartColor = platform === 'all' ? '#6366f1' : platformColors[platform] ?? '#6366f1';

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Follower Tracker</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Follower growth, new follows, and unfollows across platforms (30 days)
        </p>
      </div>

      {/* Platform filter */}
      <div className="flex items-center gap-1.5 bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-1 w-fit">
        {PLATFORMS.map((p) => (
          <button
            key={p}
            onClick={() => setPlatform(p)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors ${
              platform === p
                ? 'bg-indigo-600 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-600">Total Followers</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{fmt(currentTotal)}</p>
        </div>
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-600">Net Growth (30d)</p>
          <p className={`text-xl font-bold mt-1 ${totalNetChange >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {totalNetChange >= 0 ? '+' : ''}{fmt(totalNetChange)}
          </p>
        </div>
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-600">Growth Rate</p>
          <p className={`text-xl font-bold mt-1 ${Number(totalGrowthPct) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {Number(totalGrowthPct) >= 0 ? '+' : ''}{totalGrowthPct}%
          </p>
        </div>
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-600">New Followers</p>
          <p className="text-xl font-bold text-blue-600 dark:text-blue-400 mt-1">{fmt(totalNewFollowers)}</p>
        </div>
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-600">Unfollows</p>
          <p className="text-xl font-bold text-red-500 dark:text-red-400 mt-1">{fmt(totalUnfollows)}</p>
        </div>
      </div>

      {/* Growth chart */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Follower Growth (30d){platform !== 'all' ? ` - ${platform}` : ''}
          </h2>
          <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-600">
            <span>{fmt(startTotal)}</span>
            <span className="text-gray-300 dark:text-gray-700">&rarr;</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{fmt(currentTotal)}</span>
          </div>
        </div>
        <GrowthLine data={dailyFollowers.map((d) => d.followers)} color={chartColor} />
        <div className="flex justify-between mt-2 text-[10px] text-gray-400 dark:text-gray-600">
          <span>{dailyFollowers[0]?.date.slice(5)}</span>
          <span>{dailyFollowers[dailyFollowers.length - 1]?.date.slice(5)}</span>
        </div>
      </div>

      {/* Daily net change bar chart */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Daily Net Change
        </h2>
        <div className="flex items-end gap-[2px] h-20">
          {dailyFollowers.map((d) => {
            const maxAbs = Math.max(...dailyFollowers.map((dd) => Math.abs(dd.net_change))) || 1;
            const height = Math.max(2, (Math.abs(d.net_change) / maxAbs) * 64);
            const isPositive = d.net_change >= 0;
            return (
              <div
                key={d.date}
                className="flex-1 rounded-sm"
                style={{
                  height: `${height}px`,
                  backgroundColor: isPositive ? '#22c55e' : '#ef4444',
                  opacity: 0.7,
                  alignSelf: 'flex-end',
                }}
                title={`${d.date}: ${d.net_change >= 0 ? '+' : ''}${d.net_change}`}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-[10px] text-gray-400 dark:text-gray-600">
          <span>{dailyFollowers[0]?.date.slice(5)}</span>
          <span>{dailyFollowers[dailyFollowers.length - 1]?.date.slice(5)}</span>
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
              <tr className="text-xs text-gray-400 dark:text-gray-600 border-b border-gray-100 dark:border-gray-800">
                <th className="text-left px-5 py-3 font-medium">Platform</th>
                <th className="text-right px-4 py-3 font-medium">Current</th>
                <th className="text-right px-4 py-3 font-medium">New</th>
                <th className="text-right px-4 py-3 font-medium">Unfollows</th>
                <th className="text-right px-4 py-3 font-medium">Net</th>
                <th className="text-right px-5 py-3 font-medium">Growth</th>
              </tr>
            </thead>
            <tbody>
              {platformSummary
                .sort((a, b) => b.current - a.current)
                .map((s) => (
                  <tr key={s.platform} className="border-b border-gray-50 dark:border-gray-900 last:border-0">
                    <td className="px-5 py-3">
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded capitalize ${platformBadgeClass[s.platform] ?? ''}`}>
                        {s.platform}
                      </span>
                    </td>
                    <td className="text-right px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmt(s.current)}</td>
                    <td className="text-right px-4 py-3 text-blue-600 dark:text-blue-400 font-medium">+{fmt(s.new_followers)}</td>
                    <td className="text-right px-4 py-3 text-red-500 dark:text-red-400 font-medium">-{fmt(s.unfollows)}</td>
                    <td className="text-right px-4 py-3">
                      <span className={`font-medium ${s.net_change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {s.net_change >= 0 ? '+' : ''}{fmt(s.net_change)}
                      </span>
                    </td>
                    <td className="text-right px-5 py-3">
                      <span className={`font-semibold ${Number(s.growth_pct) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {Number(s.growth_pct) >= 0 ? '+' : ''}{s.growth_pct}%
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
