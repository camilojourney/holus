import type { PlatformStats } from '@/lib/types';

const platformColors: Record<string, string> = {
  linkedin: 'text-blue-600 dark:text-blue-400',
  instagram: 'text-pink-600 dark:text-pink-400',
  twitter: 'text-sky-500 dark:text-sky-400',
  tiktok: 'text-gray-900 dark:text-white',
  threads: 'text-gray-700 dark:text-gray-300',
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  name: string;
  stats: PlatformStats;
}

export default function PlatformCard({ name, stats }: Props) {
  const growth = stats.followers_30d_ago > 0
    ? ((stats.followers - stats.followers_30d_ago) / stats.followers_30d_ago * 100).toFixed(1)
    : '0';
  const isPositive = Number(growth) > 0;

  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-white dark:bg-gray-950">
      <div className="flex items-center justify-between mb-3">
        <span className={`text-sm font-semibold capitalize ${platformColors[name] ?? 'text-gray-700 dark:text-gray-300'}`}>
          {name}
        </span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          isPositive
            ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400'
            : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400'
        }`}>
          {isPositive ? '+' : ''}{growth}%
        </span>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">
        {fmt(stats.followers)}
      </p>
      <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">followers</p>
      <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-400 dark:text-gray-400">Posts</span>
          <p className="font-medium text-gray-700 dark:text-gray-300">{stats.posts_30d}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-400">Impr.</span>
          <p className="font-medium text-gray-700 dark:text-gray-300">{fmt(stats.impressions_30d)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-400">Eng. rate</span>
          <p className="font-medium text-gray-700 dark:text-gray-300">{(stats.engagement_rate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-400">Top type</span>
          <p className="font-medium text-gray-700 dark:text-gray-300 truncate">{stats.top_content_type}</p>
        </div>
      </div>
    </div>
  );
}
