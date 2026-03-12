import { fetchContent } from '@/lib/api';
import ContentKanban from '@/components/ContentKanban';
import ErrorBanner from '@/components/ErrorBanner';
import type { ContentItem } from '@/lib/types';

export const revalidate = 30;

export default async function ContentPage() {
  let items: ContentItem[] = [];
  let error = false;

  try {
    items = await fetchContent();
  } catch {
    error = true;
  }

  const pillarCounts = items.reduce<Record<string, number>>((acc, i) => {
    acc[i.pillar] = (acc[i.pillar] ?? 0) + 1;
    return acc;
  }, {});

  const platformCounts = items.reduce<Record<string, number>>((acc, i) => {
    acc[i.platform] = (acc[i.platform] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Content Pipeline</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Content items by stage — read-only view
        </p>
      </div>

      {error && <ErrorBanner message="Could not load content data" />}

      {!error && (
        <>
          {/* Stats row */}
          {items.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {Object.entries(pillarCounts).map(([pillar, count]) => (
                <div
                  key={pillar}
                  className="border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 bg-white dark:bg-gray-950"
                >
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{pillar}</p>
                  <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{count}</p>
                </div>
              ))}
            </div>
          )}

          <ContentKanban items={items} />

          {/* Platform distribution */}
          {items.length > 0 && (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
              <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
                Platform Distribution
              </h2>
              <div className="space-y-2">
                {Object.entries(platformCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([platform, count]) => (
                    <div key={platform} className="flex items-center gap-3">
                      <span className="text-xs text-gray-600 dark:text-gray-400 w-28 capitalize">
                        {platform}
                      </span>
                      <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-2">
                        <div
                          className="bg-indigo-500 dark:bg-indigo-400 h-2 rounded-full"
                          style={{ width: `${(count / items.length) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400 w-6 text-right">
                        {count}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
