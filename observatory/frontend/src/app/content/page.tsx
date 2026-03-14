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

  // Status counts from real data
  const counts = {
    draft: items.filter((i) => i.status === 'draft').length,
    review: items.filter((i) => i.status === 'pending_review').length,
    approved: items.filter((i) => ['approved', 'scheduled'].includes(i.status)).length,
    published: items.filter((i) => i.status === 'published').length,
    rejected: items.filter((i) => i.status === 'rejected').length,
  };

  // Platform distribution
  const platformCounts = items.reduce<Record<string, number>>((acc, i) => {
    if (i.platform) acc[i.platform] = (acc[i.platform] ?? 0) + 1;
    return acc;
  }, {});

  const countCards = [
    { label: 'Draft', value: counts.draft, color: 'text-gray-700 dark:text-gray-300' },
    { label: 'Pending Review', value: counts.review, color: 'text-yellow-700 dark:text-yellow-400' },
    { label: 'Approved', value: counts.approved, color: 'text-indigo-700 dark:text-indigo-400' },
    { label: 'Published', value: counts.published, color: 'text-green-700 dark:text-green-400' },
  ];

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Content Pipeline</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Content queue — click any card to preview, approve, or reject
        </p>
      </div>

      {error && <ErrorBanner message="Could not load content data" />}

      {!error && (
        <>
          {/* Status counts */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {countCards.map(({ label, value, color }) => (
              <div
                key={label}
                className="border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 bg-white dark:bg-gray-950"
              >
                <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
                <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          <ContentKanban items={items} />

          {/* Platform distribution */}
          {Object.keys(platformCounts).length > 0 && (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
              <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
                Platform Distribution
              </h2>
              <div className="space-y-2">
                {Object.entries(platformCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([platform, count]) => (
                    <div key={platform} className="flex items-center gap-3">
                      <span className="text-xs text-gray-600 dark:text-gray-400 w-32">
                        {platform.replace(/_/g, '/')}
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
