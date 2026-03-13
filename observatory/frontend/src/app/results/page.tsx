import { fetchResults } from '@/lib/api';
import ErrorBanner from '@/components/ErrorBanner';
import KPICard from '@/components/KPICard';
import PlatformCard from '@/components/PlatformCard';
import TopPostRow from '@/components/TopPostRow';
import GrowthChart from '@/components/GrowthChart';
import PillarBreakdown from '@/components/PillarBreakdown';
import type { GrowthData } from '@/lib/types';

export const revalidate = 30;

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default async function ResultsPage() {
  let data: GrowthData | null = null;
  let error = false;

  try {
    data = await fetchResults();
  } catch {
    error = true;
  }

  const platforms = data?.platforms ?? {};
  const totalFollowers = Object.values(platforms).reduce((s, p) => s + p.followers, 0);
  const totalFollowers30d = Object.values(platforms).reduce((s, p) => s + p.followers_30d_ago, 0);
  const followerGrowth = totalFollowers30d > 0
    ? ((totalFollowers - totalFollowers30d) / totalFollowers30d * 100).toFixed(1)
    : '0';
  const totalImpressions = Object.values(platforms).reduce((s, p) => s + p.impressions_30d, 0);
  const totalPosts = Object.values(platforms).reduce((s, p) => s + p.posts_30d, 0);
  const avgEngagement = Object.values(platforms).length > 0
    ? (Object.values(platforms).reduce((s, p) => s + p.engagement_rate, 0) / Object.values(platforms).length * 100).toFixed(1)
    : '0';

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Results</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Growth metrics and content performance across all platforms
        </p>
      </div>

      {error && <ErrorBanner message="Could not load results from Observatory API" />}

      {/* Headline KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total followers"
          value={fmt(totalFollowers)}
          subtitle={`+${followerGrowth}% in 30d`}
          color="blue"
        />
        <KPICard
          title="Impressions (30d)"
          value={fmt(totalImpressions)}
          color="default"
        />
        <KPICard
          title="Posts (30d)"
          value={totalPosts}
          color="default"
        />
        <KPICard
          title="Avg engagement"
          value={`${avgEngagement}%`}
          color={Number(avgEngagement) >= 5 ? 'green' : Number(avgEngagement) >= 3 ? 'yellow' : 'red'}
        />
      </div>

      {/* Growth chart */}
      {data && data.daily_growth.length > 0 && (
        <GrowthChart data={data.daily_growth} />
      )}

      {/* Platform breakdown */}
      {Object.keys(platforms).length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Platforms
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {Object.entries(platforms).map(([name, stats]) => (
              <PlatformCard key={name} name={name} stats={stats} />
            ))}
          </div>
        </div>
      )}

      {/* Content by pillar + product */}
      {data && Object.keys(data.content_by_pillar).length > 0 && (
        <PillarBreakdown
          byPillar={data.content_by_pillar}
          byProduct={data.content_by_product}
        />
      )}

      {/* Top performing posts */}
      {data && data.top_posts.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Top Posts
            </h2>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.top_posts.map((post) => (
              <TopPostRow key={post.id} post={post} />
            ))}
          </div>
        </div>
      )}

      {!error && !data && (
        <p className="text-sm text-gray-400 dark:text-gray-600 py-4">
          No results data available. Ensure data/results/growth.json exists.
        </p>
      )}
    </div>
  );
}
