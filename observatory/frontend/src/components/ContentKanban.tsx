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

const PILLAR_COLORS: Record<string, string> = {
  ai_engineering: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  building_in_public: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  bilingual_ai: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  systems_thinking: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
};

function QualityBadge({ score, check }: { score?: number; check?: string }) {
  if (!score && !check) return null;
  const color =
    score !== undefined
      ? score >= 75
        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
        : score >= 55
          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
      : check === 'PASS'
        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300';
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${color}`}>
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
                    className="w-full text-left rounded-lg p-3 cursor-pointer hover:border-amber-400 dark:hover:border-amber-500 hover:shadow-sm focus-ring transition-all"
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
                          className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            PILLAR_COLORS[item.content_pillar] ??
                            'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                          }`}
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
        <div className="border border-red-200 dark:border-red-900 rounded-xl bg-red-50 dark:bg-gray-900">
          <div className="px-4 py-3 border-b border-red-200 dark:border-red-900 font-semibold text-sm text-red-600 dark:text-red-400">
            Rejected
            <span className="ml-2 text-xs font-normal text-red-400 dark:text-red-700">
              ({grouped['Rejected'].length})
            </span>
          </div>
          <div className="p-3 flex flex-wrap gap-2">
            {grouped['Rejected'].map((item) => (
              <button
                key={item.id}
                onClick={() => setSelected(item)}
                className="text-left border border-red-200 dark:border-red-900 rounded-lg px-3 py-2 cursor-pointer hover:border-red-400 focus:outline-2 focus:outline-red-500 focus:outline-offset-1 transition-colors"
                style={{ background: 'var(--surface-raised)' }}
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
