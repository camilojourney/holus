'use client';

import { useState, useMemo } from 'react';
import { AreaChart, BarChart } from '@tremor/react';
import { generateFollowerData } from '@/lib/demo-data';
import RadioGroup from '@/components/RadioGroup';

const platformTremorColor: Record<string, string> = {
  linkedin: 'blue',
  instagram: 'pink',
  twitter: 'cyan',
  threads: 'gray',
  tiktok: 'slate',
};

const PLATFORMS = ['all', 'linkedin', 'instagram', 'twitter', 'threads', 'tiktok'] as const;
type Platform = typeof PLATFORMS[number];

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function FollowersPage() {
  const [platform, setPlatform] = useState<Platform>('all');

  const rawData = useMemo(() => generateFollowerData(), []);

  const filtered = useMemo(() => {
    if (platform === 'all') return rawData;
    return rawData.filter((d) => d.platform === platform);
  }, [rawData, platform]);

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
      .map(([date, v]) => ({ date, dateLabel: date.slice(5), ...v }));
  }, [filtered]);

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

  const chartColor = platform === 'all' ? 'amber' : platformTremorColor[platform] ?? 'amber';

  const areaChartData = dailyFollowers.map((d) => ({
    date: d.dateLabel,
    Followers: d.followers,
  }));

  const barChartData = dailyFollowers.map((d) => ({
    date: d.dateLabel,
    'Net Change': d.net_change,
  }));

  return (
    <div style={{ padding: 'var(--page-padding)' }} className="space-y-6 page-transition">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Audience Growth
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Acquisition, churn, and net growth trajectory by channel (30d window)
        </p>
      </div>

      {/* Platform filter */}
      <RadioGroup
        label="Filter by platform"
        options={PLATFORMS}
        value={platform}
        onChange={setPlatform}
        className="w-fit"
      />

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total Followers', value: fmt(currentTotal) },
          { label: 'Net Growth (30d)', value: `${totalNetChange >= 0 ? '+' : ''}${fmt(totalNetChange)}`, semantic: totalNetChange >= 0 ? 'var(--success)' : 'var(--danger)' },
          { label: 'Growth Rate', value: `${Number(totalGrowthPct) >= 0 ? '+' : ''}${totalGrowthPct}%`, semantic: Number(totalGrowthPct) >= 0 ? 'var(--success)' : 'var(--danger)' },
          { label: 'New Followers', value: fmt(totalNewFollowers), semantic: 'var(--info)' },
          { label: 'Unfollows', value: fmt(totalUnfollows), semantic: 'var(--danger)' },
        ].map(({ label, value, semantic }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{
              background: 'var(--surface-raised)',
              border: '1px solid var(--border-default)',
            }}
          >
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
            <p
              className="text-xl font-bold mt-1"
              style={{ color: semantic ?? 'var(--text-primary)' }}
            >
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Growth chart — Recharts */}
      <div
        className="rounded-xl p-5"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Follower Growth (30d){platform !== 'all' ? ` - ${platform}` : ''}
          </h2>
          <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
            <span>{fmt(startTotal)}</span>
            <span style={{ color: 'var(--border-strong)' }}>&rarr;</span>
            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(currentTotal)}</span>
          </div>
        </div>
        <AreaChart
          className="h-36"
          data={areaChartData}
          index="date"
          categories={['Followers']}
          colors={[chartColor]}
          curveType="natural"
          showXAxis={true}
          showYAxis={true}
          showGridLines={true}
          showLegend={false}
          autoMinValue={true}
          valueFormatter={(v: number) => fmt(v)}
          showAnimation={true}
        />
      </div>

      {/* Daily net change bar chart — Recharts */}
      <div
        className="rounded-xl p-5"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Daily Net Change
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm" style={{ background: 'var(--success)', opacity: 0.7 }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Gained</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm" style={{ background: 'var(--danger)', opacity: 0.7 }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Lost</span>
            </div>
          </div>
        </div>
        <BarChart
          className="h-20"
          data={barChartData}
          index="date"
          categories={['Net Change']}
          colors={['emerald']}
          showXAxis={false}
          showYAxis={false}
          showGridLines={false}
          showLegend={false}
          valueFormatter={(v: number) => `${v >= 0 ? '+' : ''}${v}`}
          showAnimation={true}
        />
        <div className="flex justify-between mt-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          <span>{dailyFollowers[0]?.date.slice(5)}</span>
          <span>{dailyFollowers[dailyFollowers.length - 1]?.date.slice(5)}</span>
        </div>
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
                {['Platform', 'Current', 'New', 'Unfollows', 'Net', 'Growth'].map((h, i) => (
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
              {platformSummary
                .sort((a, b) => b.current - a.current)
                .map((s) => (
                  <tr key={s.platform} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td className="px-5 py-3">
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded capitalize"
                        style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
                      >
                        {s.platform}
                      </span>
                    </td>
                    <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--text-primary)' }}>{fmt(s.current)}</td>
                    <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--info)' }}>+{fmt(s.new_followers)}</td>
                    <td className="text-right px-4 py-3 font-medium" style={{ color: 'var(--danger)' }}>-{fmt(s.unfollows)}</td>
                    <td className="text-right px-4 py-3">
                      <span className="font-medium" style={{ color: s.net_change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                        {s.net_change >= 0 ? '+' : ''}{fmt(s.net_change)}
                      </span>
                    </td>
                    <td className="text-right px-5 py-3">
                      <span className="font-semibold" style={{ color: Number(s.growth_pct) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
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
