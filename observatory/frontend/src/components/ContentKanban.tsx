'use client';

import { useState } from 'react';
import type { ContentItem, ContentDetail } from '@/lib/types';
import ContentDetailPanel from './ContentDetailPanel';

// Map API status → column
const STATUS_COLUMN: Record<string, string> = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  scheduled: 'Approved',
  published: 'Published',
  rejected: 'Rejected',
};

const COLUMNS = ['Draft', 'Pending Review', 'Approved', 'Published'];

const COLUMN_STYLES: Record<string, React.CSSProperties> = {
  'Draft': { color: 'var(--text-secondary)' },
  'Pending Review': { color: 'var(--warning)' },
  'Approved': { color: 'var(--info)' },
  'Published': { color: 'var(--success)' },
};

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LI',
  twitter_x: 'X',
  instagram: 'IG',
  threads: 'TH',
};

const PILLAR_STYLES: Record<string, React.CSSProperties> = {
  ai_engineering: { background: 'var(--pillar-engineering-bg)', color: 'var(--pillar-engineering-text)' },
  building_in_public: { background: 'var(--pillar-building-bg)', color: 'var(--pillar-building-text)' },
  bilingual_ai: { background: 'var(--pillar-bilingual-bg)', color: 'var(--pillar-bilingual-text)' },
  systems_thinking: { background: 'var(--pillar-systems-bg)', color: 'var(--pillar-systems-text)' },
};

function QualityBadge({ score, check }: { score?: number; check?: string }) {
  if (!score && !check) return null;
  const style: React.CSSProperties =
    score !== undefined
      ? score >= 75
        ? { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' }
        : score >= 55
          ? { background: 'var(--verdict-review-bg)', color: 'var(--verdict-review-text)' }
          : { background: 'var(--verdict-fail-bg)', color: 'var(--verdict-fail-text)' }
      : check === 'PASS'
        ? { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' }
        : { background: 'var(--verdict-fail-bg)', color: 'var(--verdict-fail-text)' };
  return (
    <span className="text-xs px-1.5 py-0.5 rounded font-medium" style={style}>
      {score !== undefined ? score : check}
    </span>
  );
}

interface Props {
  items: ContentItem[];
  onRefresh?: () => void;
}

export default function ContentKanban({ items, onRefresh }: Props) {
  const [selected, setSelected] = useState<ContentItem | null>(null);

  // Group by column — 'Rejected' items shown at bottom separately
  const grouped: Record<string, ContentItem[]> = Object.fromEntries(
    [...COLUMNS, 'Rejected'].map((col) => [col, []])
  );
  for (const item of items) {
    const col = STATUS_COLUMN[item.status?.toLowerCase()] ?? 'Draft';
    grouped[col].push(item);
  }

  function handleAction(updated: ContentDetail) {
    onRefresh?.();
    setSelected(null);
  }

  return (
    <>
      {/* Kanban grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map((col) => (
          <div
            key={col}
            className="rounded-xl"
            style={{
              border: '1px solid var(--border-default)',
              background: 'var(--surface-2)',
            }}
          >
            <div
              className="px-4 py-3 font-semibold text-sm"
              style={{
                borderBottom: '1px solid var(--border-default)',
                ...COLUMN_STYLES[col],
              }}
            >
              {col}
              <span className="ml-2 text-xs font-normal" style={{ color: 'var(--text-tertiary)' }}>
                ({grouped[col].length})
              </span>
            </div>
            <div className="p-3 space-y-2 min-h-24">
              {grouped[col].length === 0 ? (
                <p className="text-xs text-center py-4" style={{ color: 'var(--text-tertiary)' }}>
                  No items in stage
                </p>
              ) : (
                grouped[col].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelected(item)}
                    className="w-full text-left rounded-lg p-3 cursor-pointer hover:shadow-sm focus-ring transition-all"
                    style={{
                      background: 'var(--surface-raised)',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    <p className="text-sm font-medium line-clamp-2" style={{ color: 'var(--text-primary)' }}>
                      {item.title ?? item.id}
                    </p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {item.content_pillar && (
                        <span
                          className="text-xs px-1.5 py-0.5 rounded font-medium"
                          style={PILLAR_STYLES[item.content_pillar] ?? { background: 'var(--pillar-default-bg)', color: 'var(--pillar-default-text)' }}
                        >
                          {item.content_pillar.replace(/_/g, ' ')}
                        </span>
                      )}
                      {item.platform && (
                        <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {PLATFORM_LABELS[item.platform] ?? item.platform}
                        </span>
                      )}
                      {item.quality?.quality_score !== undefined && (
                        <QualityBadge score={item.quality.quality_score} />
                      )}
                    </div>
                    <p className="text-xs mt-1.5" style={{ color: 'var(--text-tertiary)' }}>
                      {item.content_type?.replace(/_/g, ' ')}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Rejected pieces — collapsible at bottom */}
      {grouped['Rejected'].length > 0 && (
        <div className="rounded-xl" style={{ border: '1px solid var(--rejected-border)', background: 'var(--rejected-bg)' }}>
          <div className="px-4 py-3 font-semibold text-sm" style={{ borderBottom: '1px solid var(--rejected-border)', color: 'var(--rejected-text)' }}>
            Rejected
            <span className="ml-2 text-xs font-normal" style={{ color: 'var(--rejected-text-muted)' }}>
              ({grouped['Rejected'].length})
            </span>
          </div>
          <div className="p-3 flex flex-wrap gap-2">
            {grouped['Rejected'].map((item) => (
              <button
                key={item.id}
                onClick={() => setSelected(item)}
                className="text-left rounded-lg px-3 py-2 cursor-pointer focus-ring transition-colors"
                style={{ background: 'var(--surface-raised)', border: '1px solid var(--rejected-border)' }}
              >
                <p className="text-xs font-medium line-clamp-1 max-w-48" style={{ color: 'var(--text-secondary)' }}>
                  {item.title ?? item.id}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                  {item.platform} · {item.content_type?.replace(/_/g, ' ')}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Detail panel */}
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
