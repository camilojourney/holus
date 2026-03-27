'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchContentDetail, patchContent, chooseVisual, contentImageUrl } from '@/lib/api';
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

const VERDICT_COLOR: Record<string, string> = {
  PASS: 'text-green-600 dark:text-green-400',
  PARTIAL: 'text-yellow-600 dark:text-yellow-400',
  FAIL: 'text-red-600 dark:text-red-400',
};

export default function ContentDetailPanel({ item, onClose, onAction }: Props) {
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const [selectedVisual, setSelectedVisual] = useState<'a' | 'b'>('a');
  const [scheduleDate, setScheduleDate] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

  // Auto-focus the panel when it opens
  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchContentDetail(item.id)
      .then((d) => {
        setDetail(d);
        setSelectedVisual('a');
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [item.id]);

  // Focus trap: keep Tab cycling within the panel
  const handleFocusTrap = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const panel = panelRef.current;
      if (!panel) return;

      const focusable = panel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [onClose]
  );

  async function handleApprove() {
    setActing('approve');
    try {
      // If user picked variant B, save that choice first
      if (selectedVisual === 'b' && detail?.image_b_url) {
        await chooseVisual(item.id, 'b');
      }
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

  async function handleSchedule() {
    if (!scheduleDate) return;
    setActing('schedule');
    try {
      if (selectedVisual === 'b' && detail?.image_b_url) {
        await chooseVisual(item.id, 'b');
      }
      const updated = await patchContent(item.id, {
        status: 'approved',
        scheduled_at: new Date(scheduleDate).toISOString(),
      });
      onAction(updated);
    } catch (e) {
      setError(`Schedule failed: ${String(e)}`);
    } finally {
      setActing(null);
    }
  }

  const d = detail ?? item;
  const status = d.status?.toLowerCase() ?? 'draft';
  const canAct = ['draft', 'pending_review'].includes(status);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={`Content detail: ${d.title ?? d.id}`}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="absolute inset-0 bg-black/30 dark:bg-black/50" onClick={onClose} />

      <div className="relative h-full w-full max-w-2xl bg-white dark:bg-gray-950 border-l border-gray-200 dark:border-gray-800 shadow-xl overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 px-5 py-4 flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-gray-900 dark:text-white leading-snug">
              {d.title ?? d.id}
            </p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[status] ?? STATUS_COLOR.draft}`}>
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
              {detail?.judge_verdict && (
                <span className={`text-xs font-bold ${VERDICT_COLOR[detail.judge_verdict] ?? 'text-gray-500'}`}>
                  {detail.judge_verdict} {detail.judge_score !== undefined ? `(${detail.judge_score.toFixed(2)})` : ''}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl leading-none" aria-label="Close">
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
            <p className="text-sm text-gray-400 dark:text-gray-400 animate-pulse">Loading detail…</p>
          ) : (
            <>
              {/* A/B Visual Comparison */}
              {detail?.image_url && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Companion Visual
                    {detail.image_b_url && ' — Pick A or B'}
                  </h3>

                  {detail.image_b_url ? (
                    // A/B comparison mode
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => setSelectedVisual('a')}
                          className={`rounded-xl overflow-hidden border-2 transition-all ${
                            selectedVisual === 'a'
                              ? 'border-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-800'
                              : 'border-gray-200 dark:border-gray-800 hover:border-gray-400'
                          }`}
                        >
                          <img
                            src={contentImageUrl(item.id, 'a')}
                            alt="Visual variant A"
                            className="w-full aspect-square object-cover"
                          />
                          <div className={`text-center py-1.5 text-xs font-semibold ${
                            selectedVisual === 'a' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300' : 'bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400'
                          }`}>
                            A {selectedVisual === 'a' ? '(selected)' : ''}
                          </div>
                        </button>
                        <button
                          onClick={() => setSelectedVisual('b')}
                          className={`rounded-xl overflow-hidden border-2 transition-all ${
                            selectedVisual === 'b'
                              ? 'border-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-800'
                              : 'border-gray-200 dark:border-gray-800 hover:border-gray-400'
                          }`}
                        >
                          <img
                            src={contentImageUrl(item.id, 'b')}
                            alt="Visual variant B"
                            className="w-full aspect-square object-cover"
                          />
                          <div className={`text-center py-1.5 text-xs font-semibold ${
                            selectedVisual === 'b' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300' : 'bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400'
                          }`}>
                            B {selectedVisual === 'b' ? '(selected)' : ''}
                          </div>
                        </button>
                      </div>
                      <p className="text-xs text-gray-400 dark:text-gray-400 text-center">
                        Click to select which visual to publish with this post
                      </p>
                    </div>
                  ) : (
                    // Single visual
                    <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800">
                      <img
                        src={contentImageUrl(item.id)}
                        alt="Companion visual"
                        className="w-full"
                      />
                    </div>
                  )}
                </section>
              )}

              {/* Quality */}
              {d.quality && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Quality</h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    {d.quality.hook_score && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-gray-500">Hook</span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{d.quality.hook_score}/10</span>
                      </div>
                    )}
                    {d.quality.voice_check && (
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        d.quality.voice_check === 'PASS' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                      }`}>
                        Voice: {d.quality.voice_check}
                      </span>
                    )}
                  </div>
                </section>
              )}

              {/* Full text */}
              {detail?.text && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Content
                    <span className="ml-2 normal-case font-normal text-gray-400">
                      {detail.text.split(/\s+/).filter(Boolean).length} words
                      {detail.char_count ? ` · ${detail.char_count} chars` : ` · ${detail.text.length} chars`}
                    </span>
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-4 py-3">
                    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                      {detail.text}
                    </p>
                  </div>
                  {detail.hashtags && detail.hashtags.length > 0 && (
                    <p className="mt-2 text-xs text-indigo-600 dark:text-indigo-400">{detail.hashtags.join(' ')}</p>
                  )}
                </section>
              )}

              {/* Scheduling info */}
              <section className="grid grid-cols-2 gap-3 text-xs">
                {d.created_at && (
                  <div>
                    <p className="text-gray-400 dark:text-gray-400">Created</p>
                    <p className="text-gray-700 dark:text-gray-300 mt-0.5">{new Date(d.created_at).toLocaleDateString()}</p>
                  </div>
                )}
                {d.scheduled_for && (
                  <div>
                    <p className="text-gray-400 dark:text-gray-400">Scheduled</p>
                    <p className="text-gray-700 dark:text-gray-300 mt-0.5">{new Date(d.scheduled_for).toLocaleString()}</p>
                  </div>
                )}
              </section>

              {/* Agent trace */}
              {detail?.agent_trace && detail.agent_trace.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Agent Trace</h3>
                  <ol className="space-y-2">
                    {detail.agent_trace.map((step, i) => (
                      <li key={i} className="flex items-start gap-3 text-xs border-l-2 border-indigo-200 dark:border-indigo-800 pl-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-800 dark:text-gray-200">{step.agent_id}</p>
                          {step.role && <p className="text-gray-500 dark:text-gray-400">{step.role}</p>}
                          {step.model && (
                            <span className="text-gray-400 dark:text-gray-400 font-mono">{step.model.replace('anthropic/', '')}</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
            </>
          )}
        </div>

        {/* Actions bar */}
        {canAct && (
          <div className="sticky bottom-0 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 px-5 py-4 space-y-3">
            {/* Schedule row */}
            <div className="flex items-center gap-2">
              <input
                type="datetime-local"
                value={scheduleDate}
                onChange={(e) => setScheduleDate(e.target.value)}
                className="flex-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200"
              />
              <button
                onClick={handleSchedule}
                disabled={!scheduleDate || !!acting}
                className="py-1.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors disabled:opacity-40"
              >
                {acting === 'schedule' ? 'Scheduling…' : 'Schedule'}
              </button>
            </div>

            {/* Approve / Reject row */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleApprove}
                disabled={!!acting}
                className="flex-1 py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {acting === 'approve' ? 'Approving…' : 'Approve & Post Now'}
              </button>
              <button
                onClick={handleReject}
                disabled={!!acting}
                className="flex-1 py-2 px-4 rounded-lg border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {acting === 'reject' ? 'Rejecting…' : 'Reject'}
              </button>
            </div>
          </div>
        )}

        {!canAct && (
          <div className="sticky bottom-0 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 px-5 py-4">
            <p className="text-xs text-gray-400 dark:text-gray-400">
              No actions available for {STATUS_LABEL[status] ?? status} pieces.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
