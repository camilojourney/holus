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

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  draft: { background: 'var(--status-draft-bg)', color: 'var(--status-draft-text)' },
  pending_review: { background: 'var(--status-pending-bg)', color: 'var(--status-pending-text)' },
  approved: { background: 'var(--status-approved-bg)', color: 'var(--status-approved-text)' },
  scheduled: { background: 'var(--status-approved-bg)', color: 'var(--status-approved-text)' },
  published: { background: 'var(--status-published-bg)', color: 'var(--status-published-text)' },
  rejected: { background: 'var(--status-rejected-bg)', color: 'var(--status-rejected-text)' },
};

const VERDICT_STYLE: Record<string, React.CSSProperties> = {
  PASS: { color: 'var(--verdict-pass-text)' },
  PARTIAL: { color: 'var(--verdict-review-text)' },
  FAIL: { color: 'var(--verdict-fail-text)' },
};

export default function ContentDetailPanel({ item, onClose, onAction }: Props) {
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const [selectedVisual, setSelectedVisual] = useState<'a' | 'b'>('a');
  const [scheduleDate, setScheduleDate] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

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

  const handleFocusTrap = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') { onClose(); return; }
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
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    },
    [onClose]
  );

  async function handleApprove() {
    setActing('approve');
    try {
      if (selectedVisual === 'b' && detail?.image_b_url) await chooseVisual(item.id, 'b');
      const updated = await patchContent(item.id, { status: 'approved' });
      onAction(updated);
    } catch (e) { setError(`Approve failed: ${String(e)}`); }
    finally { setActing(null); }
  }

  async function handleReject() {
    setActing('reject');
    try {
      const updated = await patchContent(item.id, { status: 'rejected' });
      onAction(updated);
    } catch (e) { setError(`Reject failed: ${String(e)}`); }
    finally { setActing(null); }
  }

  async function handleSchedule() {
    if (!scheduleDate) return;
    setActing('schedule');
    try {
      if (selectedVisual === 'b' && detail?.image_b_url) await chooseVisual(item.id, 'b');
      const updated = await patchContent(item.id, { status: 'approved', scheduled_at: new Date(scheduleDate).toISOString() });
      onAction(updated);
    } catch (e) { setError(`Schedule failed: ${String(e)}`); }
    finally { setActing(null); }
  }

  const d = detail ?? item;
  const status = d.status?.toLowerCase() ?? 'draft';
  const canAct = ['draft', 'pending_review'].includes(status);

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-start justify-end outline-none"
      role="dialog"
      aria-modal="true"
      aria-label={`Content detail: ${d.title ?? d.id}`}
      onKeyDown={handleFocusTrap}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="absolute inset-0 panel-backdrop" style={{ background: 'var(--surface-overlay)' }} onClick={onClose} />

      <div
        className="relative h-full w-full max-w-2xl shadow-xl overflow-y-auto flex flex-col panel-slide-in"
        style={{ background: 'var(--surface-raised)', borderLeft: '1px solid var(--border-default)' }}
      >
        <div
          className="sticky top-0 z-10 px-5 py-4 flex items-start gap-3"
          style={{ background: 'var(--surface-raised)', borderBottom: '1px solid var(--border-default)' }}
        >
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold leading-snug" style={{ color: 'var(--text-primary)' }}>
              {d.title ?? d.id}
            </p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={STATUS_STYLE[status] ?? STATUS_STYLE.draft}>
                {STATUS_LABEL[status] ?? status}
              </span>
              {d.platform && <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{d.platform.replace('_', '/')}</span>}
              {d.content_type && <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{d.content_type.replace(/_/g, ' ')}</span>}
              {detail?.judge_verdict && (
                <span
                  className="text-xs font-bold"
                  style={VERDICT_STYLE[detail.judge_verdict] ?? { color: 'var(--text-tertiary)' }}
                >
                  {detail.judge_verdict} {detail.judge_score !== undefined ? `(${detail.judge_score.toFixed(2)})` : ''}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-xl leading-none focus-ring rounded transition-colors" style={{ color: 'var(--text-tertiary)' }} aria-label="Close">&times;</button>
        </div>

        <div className="flex-1 px-5 py-4 space-y-5">
          {error && (
            <p className="text-sm rounded-lg px-3 py-2" style={{ color: 'var(--verdict-fail-text)', background: 'var(--verdict-fail-bg)', border: '1px solid var(--rejected-border)' }}>{error}</p>
          )}

          {loading ? (
            <p className="text-sm animate-pulse" style={{ color: 'var(--text-tertiary)' }}>Loading detail...</p>
          ) : (
            <>
              {detail?.image_url && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-tertiary)' }}>
                    Companion Visual{detail.image_b_url && ' -- Pick A or B'}
                  </h3>
                  {detail.image_b_url ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => setSelectedVisual('a')}
                          className="rounded-xl overflow-hidden border-2 transition-all"
                          style={{ borderColor: selectedVisual === 'a' ? 'var(--brand)' : 'var(--border-default)', boxShadow: selectedVisual === 'a' ? '0 0 0 2px var(--brand-muted-oklch)' : 'none' }}
                        >
                          <img src={contentImageUrl(item.id, 'a')} alt="Visual variant A" className="w-full aspect-square object-cover" />
                          <div className="text-center py-1.5 text-xs font-semibold" style={{ background: selectedVisual === 'a' ? 'var(--warning-subtle)' : 'var(--surface-2)', color: selectedVisual === 'a' ? 'var(--warning)' : 'var(--text-tertiary)' }}>
                            A {selectedVisual === 'a' ? '(selected)' : ''}
                          </div>
                        </button>
                        <button
                          onClick={() => setSelectedVisual('b')}
                          className="rounded-xl overflow-hidden border-2 transition-all"
                          style={{ borderColor: selectedVisual === 'b' ? 'var(--brand)' : 'var(--border-default)', boxShadow: selectedVisual === 'b' ? '0 0 0 2px var(--brand-muted-oklch)' : 'none' }}
                        >
                          <img src={contentImageUrl(item.id, 'b')} alt="Visual variant B" className="w-full aspect-square object-cover" />
                          <div className="text-center py-1.5 text-xs font-semibold" style={{ background: selectedVisual === 'b' ? 'var(--warning-subtle)' : 'var(--surface-2)', color: selectedVisual === 'b' ? 'var(--warning)' : 'var(--text-tertiary)' }}>
                            B {selectedVisual === 'b' ? '(selected)' : ''}
                          </div>
                        </button>
                      </div>
                      <p className="text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>Click to select which visual to publish with this post</p>
                    </div>
                  ) : (
                    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border-default)' }}>
                      <img src={contentImageUrl(item.id)} alt="Companion visual" className="w-full" />
                    </div>
                  )}
                </section>
              )}

              {d.quality && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-tertiary)' }}>Quality</h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    {d.quality.hook_score && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Hook</span>
                        <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{d.quality.hook_score}/10</span>
                      </div>
                    )}
                    {d.quality.voice_check && (
                      <span className="text-xs px-2 py-0.5 rounded font-medium" style={d.quality.voice_check === 'PASS' ? { background: 'var(--verdict-pass-bg)', color: 'var(--verdict-pass-text)' } : { background: 'var(--verdict-fail-bg)', color: 'var(--verdict-fail-text)' }}>
                        Voice: {d.quality.voice_check}
                      </span>
                    )}
                  </div>
                </section>
              )}

              {detail?.text && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-tertiary)' }}>
                    Content
                    <span className="ml-2 normal-case font-normal">
                      {detail.text.split(/\s+/).filter(Boolean).length} words
                      {detail.char_count ? ` · ${detail.char_count} chars` : ` · ${detail.text.length} chars`}
                    </span>
                  </h3>
                  <div className="rounded-lg px-4 py-3" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-default)' }}>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{detail.text}</p>
                  </div>
                  {detail.hashtags && detail.hashtags.length > 0 && (
                    <p className="mt-2 text-xs" style={{ color: 'var(--brand)' }}>{detail.hashtags.join(' ')}</p>
                  )}
                </section>
              )}

              <section className="grid grid-cols-2 gap-3 text-xs">
                {d.created_at && (
                  <div>
                    <p style={{ color: 'var(--text-tertiary)' }}>Created</p>
                    <p className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>{new Date(d.created_at).toLocaleDateString()}</p>
                  </div>
                )}
                {d.scheduled_for && (
                  <div>
                    <p style={{ color: 'var(--text-tertiary)' }}>Scheduled</p>
                    <p className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>{new Date(d.scheduled_for).toLocaleString()}</p>
                  </div>
                )}
              </section>

              {detail?.agent_trace && detail.agent_trace.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-tertiary)' }}>Agent Trace</h3>
                  <ol className="space-y-2">
                    {detail.agent_trace.map((step, i) => (
                      <li key={i} className="flex items-start gap-3 text-xs pl-3" style={{ borderLeft: '2px solid var(--brand-muted-oklch)' }}>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>{step.agent_id}</p>
                          {step.role && <p style={{ color: 'var(--text-tertiary)' }}>{step.role}</p>}
                          {step.model && <span className="font-mono" style={{ color: 'var(--text-tertiary)' }}>{step.model.replace('anthropic/', '')}</span>}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
            </>
          )}
        </div>

        {canAct && (
          <div className="sticky bottom-0 px-5 py-4 space-y-3" style={{ background: 'var(--surface-raised)', borderTop: '1px solid var(--border-default)' }}>
            <div className="flex items-center gap-2">
              <input
                type="datetime-local"
                value={scheduleDate}
                onChange={(e) => setScheduleDate(e.target.value)}
                className="flex-1 text-sm rounded-lg px-3 py-1.5 focus-ring"
                style={{ border: '1px solid var(--border-default)', background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
              />
              <button onClick={handleSchedule} disabled={!scheduleDate || !!acting} className="py-1.5 px-4 rounded-lg text-sm font-semibold transition-colors disabled:opacity-40 focus-ring" style={{ background: 'var(--button-schedule-bg)', color: 'var(--text-inverse)' }}>
                {acting === 'schedule' ? 'Scheduling...' : 'Schedule'}
              </button>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={handleApprove} disabled={!!acting} className="flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 focus-ring" style={{ background: 'var(--button-approve-bg)', color: 'var(--text-inverse)' }}>
                {acting === 'approve' ? 'Approving...' : 'Approve & Post Now'}
              </button>
              <button onClick={handleReject} disabled={!!acting} className="flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 focus-ring" style={{ border: '1px solid var(--button-reject-border)', color: 'var(--button-reject-text)' }}>
                {acting === 'reject' ? 'Rejecting...' : 'Reject'}
              </button>
            </div>
          </div>
        )}

        {!canAct && (
          <div className="sticky bottom-0 px-5 py-4" style={{ background: 'var(--surface-raised)', borderTop: '1px solid var(--border-default)' }}>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>No actions available for {STATUS_LABEL[status] ?? status} pieces.</p>
          </div>
        )}
      </div>
    </div>
  );
}
