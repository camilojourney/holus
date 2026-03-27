import { fetchContent } from '@/lib/api';
import ContentKanban from '@/components/ContentKanban';
import ErrorBanner from '@/components/ErrorBanner';
import PlatformDistribution from '@/components/PlatformDistribution';
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
    { label: 'Drafting', value: counts.draft, color: 'var(--text-secondary)' },
    { label: 'Awaiting Review', value: counts.review, color: 'var(--warning)' },
    { label: 'Gate Passed', value: counts.approved, color: 'var(--info)' },
    { label: 'Live', value: counts.published, color: 'var(--success)' },
  ];

  return (
    <div className="px-6 py-6 space-y-6 page-transition">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Content Pipeline</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Stage gates from draft to publish -- click any card to inspect, calibrate, or reject
        </p>
      </div>

      {error && <ErrorBanner message="Could not load content data" />}

      {!error && (
        <>
          {/* Status counts */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {countCards.map(({ label, value, color }, i) => (
              <div
                key={label}
                className={`rounded-xl px-4 py-3 animate-fade-in stagger-${i + 1}`}
                style={{
                  border: '1px solid var(--border-default)',
                  background: 'var(--surface-raised)',
                }}
              >
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
                <p className="text-xl font-bold mt-1" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>

          <ContentKanban items={items} />

          {/* Platform distribution */}
          {Object.keys(platformCounts).length > 0 && (
            <PlatformDistribution platformCounts={platformCounts} />
          )}
        </>
      )}
    </div>
  );
}
