import type { TopPost } from '@/lib/types';

const platformBadge: Record<string, string> = {
  linkedin: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
  instagram: 'bg-pink-50 text-pink-700 dark:bg-pink-950 dark:text-pink-400',
  twitter: 'bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-400',
  tiktok: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  threads: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  post: TopPost;
}

export default function TopPostRow({ post }: Props) {
  const date = new Date(post.published_at);
  const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;

  return (
    <div className="px-5 py-3.5 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {post.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded capitalize ${platformBadge[post.platform] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}`}>
            {post.platform}
          </span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-400 capitalize">
            {post.product}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-600">{dateStr}</span>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 shrink-0">
        <div className="text-right">
          <p className="font-medium text-gray-700 dark:text-gray-300">{fmt(post.impressions)}</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-600">views</p>
        </div>
        <div className="text-right">
          <p className="font-medium text-gray-700 dark:text-gray-300">{fmt(post.likes)}</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-600">likes</p>
        </div>
        <div className="text-right">
          <p className="font-medium text-gray-700 dark:text-gray-300">{fmt(post.shares)}</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-600">shares</p>
        </div>
        <div className="text-right w-12">
          <p className={`font-semibold ${post.engagement_rate >= 0.07 ? 'text-green-600 dark:text-green-400' : post.engagement_rate >= 0.04 ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-600 dark:text-gray-400'}`}>
            {(post.engagement_rate * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-gray-400 dark:text-gray-600">eng.</p>
        </div>
      </div>
    </div>
  );
}
