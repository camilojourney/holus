'use client';

import { useState, useEffect } from 'react';
import { fetchContentDetail, patchContent } from '@/lib/api';
import type { ContentItem, ContentDetail } from '@/lib/types';

interface Props {
  item: ContentItem;
  onClose: () => void;
  onAction: (updated: ContentDetail) => void;
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  scheduled: 'Scheduled',
  published: 'Published',
  rejected: 'Rejected',
};

const STATUS_COLOR: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  pending_review: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  approved: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  scheduled: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  published: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

export default function ContentDetailPanel({ item, onClose, onAction }: Props) {
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null); // 'approve' | 'reject'

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchContentDetail(item.id)
      .then(setDetail)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [item.id]);

  async function handleApprove() {
    setActing('approve');
    try {
      const updated = await patchContent(item.id, { status: 'approved' });
      onAction(updated);
    } catch (e) {
      setError(`Approve failed: ${String(e)}`);
    } finally {
      setActing(null);
    }
  }

  async function handleReject() {
    setActing('reject');
    try {
      const updated = await patchContent(item.id, { status: 'rejected' });
      onAction(updated);
    } catch (e) {
      setError(`Reject failed: ${String(e)}`);
    } finally {
      setActing(null);
    }
  }

  const d = detail ?? item;
  const status = d.status?.toLowerCase() ?? 'draft';
  const canApprove = ['draft', 'pending_review'].includes(status);
  const canReject = ['draft', 'pending_review', 'approved', 'scheduled'].includes(status);

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="absolute inset-0 bg-black/30 dark:bg-black/50" onClick={onClose} />

      {/* Panel */}
      <div className="relative h-full w-full max-w-xl bg-white dark:bg-gray-950 border-l border-gray-200 dark:border-gray-800 shadow-xl overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 px-5 py-4 flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-gray-900 dark:text-white leading-snug">
              {d.title ?? d.id}
            </p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  STATUS_COLOR[status] ?? STATUS_COLOR.draft
                }`}
              >
                {STATUS_LABEL[status] ?? status}
              </span>
              {d.platform && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {d.platform.replace('_', '/')}
                </span>
              )}
              {d.content_type && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {d.content_type.replace(/_/g, ' ')}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl leading-none flex-shrink-0"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 px-5 py-4 space-y-5">
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-sm text-gray-400 dark:text-gray-600 animate-pulse">
              Loading detail…
            </p>
          ) : (
            <>
              {/* Quality */}
              {d.quality && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Quality
                  </h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    {d.quality.quality_score !== undefined && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-gray-500">Score</span>
                        <span
                          className={`text-sm font-bold ${
                            d.quality.quality_score >= 75
                              ? 'text-green-600 dark:text-green-400'
                              : d.quality.quality_score >= 55
                                ? 'text-yellow-600 dark:text-yellow-400'
                                : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {d.quality.quality_score}
                        </span>
                      </div>
                    )}
                    {d.quality.hook_score && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-gray-500">Hook</span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {d.quality.hook_score}/10
                        </span>
                      </div>
                    )}
                    {d.quality.voice_check && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-medium ${
                          d.quality.voice_check === 'PASS'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                        }`}
                      >
                        Voice: {d.quality.voice_check}
                      </span>
                    )}
                  </div>
                  {d.quality.violations && d.quality.violations.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {d.quality.violations.map((v, i) => (
                        <li key={i} className="text-xs text-red-600 dark:text-red-400 flex items-start gap-1">
                          <span>⚠</span>
                          <span>{v}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              {/* Full text */}
              {(detail as ContentDetail | null)?.text && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Content
                    {(detail as ContentDetail).char_count && (
                      <span className="ml-2 normal-case font-normal text-gray-400">
                        {(detail as ContentDetail).char_count} chars
                      </span>
                    )}
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-4 py-3">
                    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                      {(detail as ContentDetail).text}
                    </p>
                  </div>
                  {(detail as ContentDetail).hashtags && (detail as ContentDetail).hashtags!.length > 0 && (
                    <p className="mt-2 text-xs text-indigo-600 dark:text-indigo-400">
                      {(detail as ContentDetail).hashtags!.join(' ')}
                    </p>
                  )}
                </section>
              )}

              {/* Scheduling */}
              <section className="grid grid-cols-2 gap-3 text-xs">
                {d.created_at && (
                  <div>
                    <p className="text-gray-400 dark:text-gray-600">Created</p>
                    <p className="text-gray-700 dark:text-gray-300 mt-0.5">
                      {new Date(d.created_at).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {d.scheduled_for && (
                  <div>
                    <p className="text-gray-400 dark:text-gray-600">Scheduled</p>
                    <p className="text-gray-700 dark:text-gray-300 mt-0.5">
                      {new Date(d.scheduled_for).toLocaleString()}
                    </p>
                  </div>
                )}
                {d.idea_source && (
                  <div className="col-span-2">
                    <p className="text-gray-400 dark:text-gray-600">Idea source</p>
                    <p className="text-gray-700 dark:text-gray-300 mt-0.5 line-clamp-2">{d.idea_source}</p>
                  </div>
                )}
              </section>

              {/* Agent trace */}
              {(detail as ContentDetail | null)?.agent_trace && (detail as ContentDetail).agent_trace!.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Agent Trace
                  </h3>
                  <ol className="space-y-2">
                    {(detail as ContentDetail).agent_trace!.map((step, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-3 text-xs border-l-2 border-indigo-200 dark:border-indigo-800 pl-3"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-800 dark:text-gray-200">
                            {step.agent_id}
                          </p>
                          {step.role && (
                            <p className="text-gray-500 dark:text-gray-400">{step.role}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            {step.model && (
                              <span className="text-gray-400 dark:text-gray-600 font-mono">
                                {step.model.replace('anthropic/', '')}
                              </span>
                            )}
                            {step.quality_score && (
                              <span className="text-green-600 dark:text-green-400">
                                score: {step.quality_score}
                              </span>
                            )}
                            {step.verdict && (
                              <span
                                className={
                                  step.verdict === 'PASS'
                                    ? 'text-green-600 dark:text-green-400'
                                    : 'text-red-600 dark:text-red-400'
                                }
                              >
                                {step.verdict}
                              </span>
                            )}
                          </div>
                        </div>
                        {step.at && (
                          <span className="text-gray-400 dark:text-gray-600 flex-shrink-0">
                            {new Date(step.at).toLocaleTimeString()}
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>
                </section>
              )}
            </>
          )}
        </div>

        {/* Actions */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 px-5 py-4 flex items-center gap-3">
          {canApprove && (
            <button
              onClick={handleApprove}
              disabled={!!acting}
              className="flex-1 py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {acting === 'approve' ? 'Approving…' : 'Approve'}
            </button>
          )}
          {canReject && (
            <button
              onClick={handleReject}
              disabled={!!acting}
              className="flex-1 py-2 px-4 rounded-lg border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {acting === 'reject' ? 'Rejecting…' : 'Reject'}
            </button>
          )}
          {!canApprove && !canReject && (
            <p className="text-xs text-gray-400 dark:text-gray-600">
              No actions available for {STATUS_LABEL[status] ?? status} pieces.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
