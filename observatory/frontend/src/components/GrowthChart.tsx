'use client';

import type { DailyGrowth } from '@/lib/types';

interface Props {
  data: DailyGrowth[];
}

export default function GrowthChart({ data }: Props) {
  if (data.length < 2) return null;

  const followers = data.map((d) => d.total_followers);
  const min = Math.min(...followers);
  const max = Math.max(...followers);
  const range = max - min || 1;

  const width = 800;
  const height = 160;
  const padding = { top: 10, right: 10, bottom: 24, left: 10 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const points = data.map((d, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartW;
    const y = padding.top + chartH - ((d.total_followers - min) / range) * chartH;
    return { x, y, ...d };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

  // Show ~6 evenly spaced date labels
  const labelStep = Math.max(1, Math.floor(data.length / 6));

  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Follower Growth (30d)
        </h2>
        <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-400">
          <span>{min.toLocaleString()}</span>
          <span className="text-gray-300 dark:text-gray-700">→</span>
          <span className="font-medium text-gray-700 dark:text-gray-300">{max.toLocaleString()}</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" aria-label="Follower growth chart">
        <defs>
          <linearGradient id="growthFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(99 102 241)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="rgb(99 102 241)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#growthFill)" />
        <path d={linePath} fill="none" stroke="rgb(99 102 241)" strokeWidth="2" />
        {points.map((p, i) =>
          i % labelStep === 0 || i === points.length - 1 ? (
            <text
              key={p.date}
              x={p.x}
              y={height - 4}
              textAnchor="middle"
              className="fill-gray-400 dark:fill-gray-400"
              fontSize="10"
            >
              {p.date.slice(5)}
            </text>
          ) : null
        )}
      </svg>
    </div>
  );
}
