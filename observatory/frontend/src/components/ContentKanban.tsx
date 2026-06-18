'use client';

import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { ContentItem } from '@/lib/types';
import ContentDetailPanel from './ContentDetailPanel';

const STATUS_LABEL: Record<string, string> = {
  draft: 'Draft',
  pending_review: 'Review',
  approved: 'Approved',
  scheduled: 'Scheduled',
  published: 'Published',
  rejected: 'Rejected',
};

const STATUS_STYLE: Record<string, CSSProperties> = {
  draft: { background: 'var(--status-draft-bg)', color: 'var(--status-draft-text)' },
  pending_review: { background: 'var(--status-pending-bg)', color: 'var(--status-pending-text)' },
  approved: { background: 'var(--status-approved-bg)', color: 'var(--status-approved-text)' },
  scheduled: { background: 'var(--status-approved-bg)', color: 'var(--status-approved-text)' },
  published: { background: 'var(--status-published-bg)', color: 'var(--status-published-text)' },
  rejected: { background: 'var(--status-rejected-bg)', color: 'var(--status-rejected-text)' },
};

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LI',
  facebook: 'FB',
  twitter_x: 'X',
  twitter: 'X',
  instagram: 'IG',
  threads: 'TH',
};

const PLATFORM_NAMES: Record<string, string> = {
  linkedin: 'LinkedIn',
  facebook: 'Facebook',
  twitter_x: 'X',
  twitter: 'X',
  instagram: 'Instagram',
  threads: 'Threads',
};

const CONTENT_TYPE_NAMES: Record<string, string> = {
  authority_post: 'Authority post',
  caption: 'Caption',
  carousel_outline: 'Carousel',
  educational: 'Educational post',
  image_caption: 'Image',
  text_post: 'Post',
  thread: 'Thread',
};

const PLATFORM_ORDER = ['linkedin', 'instagram', 'threads', 'twitter_x', 'twitter', 'facebook'];

interface Props {
  items: ContentItem[];
  title?: string;
  description?: string;
  maxPerColumn?: number;
  onRefresh?: () => void;
}

interface ThoughtGroup {
  key: string;
  title: string;
  sourcePreview: string;
  createdAt: number;
  items: ContentItem[];
  allItems: ContentItem[];
  outputVersions: Record<string, number>;
}

function itemTime(item: ContentItem): number {
  return new Date(item.created_at ?? 0).getTime() || 0;
}

function truncate(value: string | undefined, max: number): string {
  if (!value) return '';
  const trimmed = value.trim().replace(/\s+/g, ' ');
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 3).trim()}...`;
}

function formatContentType(item: ContentItem): string {
  if (item.platform === 'instagram' && item.content_type === 'image_caption') {
    return 'Instagram Image';
  }
  if ((item.platform === 'twitter_x' || item.platform === 'twitter') && item.content_type === 'thread') {
    return 'X Thread';
  }
  const platform = item.platform ? PLATFORM_NAMES[item.platform] ?? item.platform : null;
  const contentType = CONTENT_TYPE_NAMES[item.content_type] ?? item.content_type?.replace(/_/g, ' ');
  return [platform, contentType].filter(Boolean).join(' ');
}

function statusKey(item: ContentItem): string {
  return item.status?.toLowerCase() || 'draft';
}

function qualityStatus(item: ContentItem): { label: string; style: CSSProperties } | null {
  const score = item.quality?.quality_score;
  if (typeof score === 'number') {
    const normalized = score <= 10 ? score * 10 : score;
    const style =
      normalized >= 75
        ? { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' }
        : normalized >= 55
          ? { background: 'var(--verdict-review-bg)', color: 'var(--verdict-review-text)' }
          : { background: 'var(--verdict-fail-bg)', color: 'var(--verdict-fail-text)' };
    return { label: `${score}`, style };
  }
  const check = item.quality?.voice_check;
  if (!check) return null;
  return {
    label: check,
    style:
      check === 'PASS'
        ? { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' }
        : { background: 'var(--verdict-fail-bg)', color: 'var(--verdict-fail-text)' },
  };
}

function platformRank(item: ContentItem): number {
  const index = PLATFORM_ORDER.indexOf(item.platform ?? '');
  return index === -1 ? PLATFORM_ORDER.length : index;
}

function thoughtKey(item: ContentItem): string {
  const source = item.idea_source || item.title || item.group_id || item.id;
  return source.trim().toLowerCase().replace(/\s+/g, ' ').slice(0, 260);
}

function outputKey(item: ContentItem): string {
  return `${item.platform ?? 'unknown'}:${item.content_type}`;
}

function groupContentSets(items: ContentItem[]): ThoughtGroup[] {
  const groups = new Map<string, ContentItem[]>();
  for (const item of items) {
    const key = thoughtKey(item);
    const group = groups.get(key) ?? [];
    group.push(item);
    groups.set(key, group);
  }

  return Array.from(groups.entries())
    .map(([key, groupItems]) => {
      const latestByOutput = new Map<string, ContentItem>();
      const outputVersions: Record<string, number> = {};
      for (const item of groupItems) {
        const key = outputKey(item);
        outputVersions[key] = (outputVersions[key] ?? 0) + 1;
        const current = latestByOutput.get(key);
        if (!current || itemTime(item) > itemTime(current)) {
          latestByOutput.set(key, item);
        }
      }

      const sorted = Array.from(latestByOutput.values()).sort((a, b) => {
        const platformDiff = platformRank(a) - platformRank(b);
        if (platformDiff !== 0) return platformDiff;
        return formatContentType(a).localeCompare(formatContentType(b));
      });
      const newest = Math.max(...groupItems.map(itemTime));
      const lead = [...groupItems].sort((a, b) => itemTime(b) - itemTime(a))[0];
      return {
        key,
        title: lead.title ?? (truncate(lead.idea_source, 90) || lead.id),
        sourcePreview: truncate(lead.idea_source, 180),
        createdAt: newest,
        items: sorted,
        allItems: groupItems,
        outputVersions,
      };
    })
    .sort((a, b) => b.createdAt - a.createdAt);
}

function groupStatusSummary(items: ContentItem[]): string {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = statusKey(item);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([status, count]) => `${count} ${STATUS_LABEL[status] ?? status}`)
    .join(' · ');
}

function outputKindCounts(group: ThoughtGroup): string {
  const { items, allItems } = group;
  const visuals = items.filter((item) =>
    ['image_caption', 'carousel_outline'].includes(item.content_type)
  ).length;
  const copy = Math.max(items.length - visuals, 0);
  const versions = allItems.length > items.length ? ` · ${allItems.length} versions` : '';
  return `${items.length} outputs · ${copy} copy · ${visuals} visual${versions}`;
}

export default function ContentKanban({
  items,
  title = 'Review queue',
  description,
  maxPerColumn = 6,
  onRefresh,
}: Props) {
  const [selected, setSelected] = useState<ContentItem | null>(null);
  const groups = useMemo(() => groupContentSets(items), [items]);
  const visibleGroups = groups.slice(0, maxPerColumn);
  const hiddenGroups = Math.max(groups.length - visibleGroups.length, 0);

  function handleAction() {
    onRefresh?.();
    setSelected(null);
  }

  return (
    <>
      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              {title}
            </h2>
            {description && (
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                {description}
              </p>
            )}
          </div>
          <span className="text-xs text-right" style={{ color: 'var(--text-tertiary)' }}>
            Showing {visibleGroups.length} of {groups.length} thoughts · {items.length} outputs
          </span>
        </div>

        <div className="space-y-3">
          {visibleGroups.length === 0 ? (
            <div
              className="rounded-xl px-4 py-8 text-center"
              style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)' }}
            >
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No content sets ready for review.
              </p>
            </div>
          ) : (
            visibleGroups.map((group) => (
              <section
                key={group.key}
                className="rounded-xl overflow-hidden"
                style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)' }}
              >
                <div
                  className="px-4 py-3"
                  style={{ borderBottom: '1px solid var(--border-default)', background: 'var(--surface-raised)' }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p
                        className="text-xs font-semibold uppercase"
                        style={{ color: 'var(--text-tertiary)', letterSpacing: '0.12em' }}
                      >
                        Thought set
                      </p>
                      <h3 className="mt-1 text-lg font-semibold leading-snug" style={{ color: 'var(--text-primary)' }}>
                        {group.title}
                      </h3>
                      {group.sourcePreview && (
                        <p className="mt-1 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                          {group.sourcePreview}
                        </p>
                      )}
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                        {outputKindCounts(group)}
                      </p>
                      <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {groupStatusSummary(group.items)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
                  {group.items.map((item, index) => {
                    const quality = qualityStatus(item);
                    const status = statusKey(item);
                    const versions = group.outputVersions[outputKey(item)] ?? 1;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setSelected(item)}
                        className="min-h-32 p-4 text-left focus-ring transition-colors"
                        style={{
                          borderTop: index < 4 ? 'none' : '1px solid var(--border-default)',
                          borderRight: index % 4 === 3 ? 'none' : '1px solid var(--border-default)',
                          background: 'transparent',
                        }}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold leading-snug" style={{ color: 'var(--text-primary)' }}>
                              {formatContentType(item)}
                            </p>
                            <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                              {item.platform ? PLATFORM_LABELS[item.platform] ?? item.platform : 'NA'}
                              {item.posting_destination?.handle ? ` · ${item.posting_destination.handle}` : ''}
                            </p>
                          </div>
                          <span
                            className="text-xs px-2 py-0.5 rounded-full font-medium"
                            style={STATUS_STYLE[status] ?? STATUS_STYLE.draft}
                          >
                            {STATUS_LABEL[status] ?? status}
                          </span>
                        </div>
                        <div className="mt-4 flex items-center gap-2 flex-wrap">
                          {versions > 1 && (
                            <span
                              className="text-xs px-2 py-0.5 rounded"
                              style={{ background: 'var(--surface-raised)', color: 'var(--text-tertiary)' }}
                            >
                              {versions} versions
                            </span>
                          )}
                          {quality && (
                            <span className="text-xs px-2 py-0.5 rounded font-medium" style={quality.style}>
                              {quality.label}
                            </span>
                          )}
                          {item.content_pillar && (
                            <span
                              className="text-xs px-2 py-0.5 rounded"
                              style={{ background: 'var(--pillar-default-bg)', color: 'var(--pillar-default-text)' }}
                            >
                              {item.content_pillar.replace(/_/g, ' ')}
                            </span>
                          )}
                        </div>
                        <p className="mt-3 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                          {truncate(item.title ?? item.id, 86)}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))
          )}
        </div>

        {hiddenGroups > 0 && (
          <p className="text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>
            {hiddenGroups} older thought sets hidden
          </p>
        )}
      </section>

      {selected && (
        <ContentDetailPanel
          item={selected}
          onClose={() => setSelected(null)}
          onAction={handleAction}
        />
      )}
    </>
  );
}
