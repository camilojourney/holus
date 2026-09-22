'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle,
  CheckCircle2,
  Link2,
  Paperclip,
  Send,
  Sparkles,
} from 'lucide-react';
import {
  confirmCapture,
  previewCapture,
  suggestCapture,
} from '@/lib/api';
import { resolveConnection } from '@/lib/connection';
import type {
  CaptureConfirmResult,
  CaptureRouteSuggestion,
  ContentDetail,
} from '@/lib/types';

type Step = 'capture' | 'suggest' | 'preview' | 'done';
type RetryAction = 'suggest' | 'preview' | 'confirm' | null;

function looksLikeUrl(value: string): boolean {
  return /^https?:\/\/\S+/i.test(value.trim());
}

function attachmentError(file: File): string | null {
  const accepted = file.type.startsWith('image/') || file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  return accepted ? null : 'Unsupported attachment. Choose an image or PDF.';
}

function friendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (/failed to fetch|network|load failed|fetch/i.test(message)) {
    return 'Holus backend is unavailable. Check the local connection and try again.';
  }
  if (/400|422|unsupported|attachment/i.test(message)) {
    return message.replace(/^POST \/capture\/\w+ → \d+:?\s*/i, '') || 'This capture or attachment was rejected.';
  }
  return message;
}

export default function CaptureShare() {
  const router = useRouter();
  const connection = resolveConnection();
  const live = connection.kind === 'local_dev';

  const [text, setText] = useState('');
  const [attachmentInput, setAttachmentInput] = useState('');
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileType, setFileType] = useState<string | null>(null);
  const [step, setStep] = useState<Step>('capture');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<CaptureRouteSuggestion[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [previews, setPreviews] = useState<ContentDetail[]>([]);
  const [deliveryGranted, setDeliveryGranted] = useState(false);
  const [socialReachable, setSocialReachable] = useState<boolean | null>(null);
  const [confirmResults, setConfirmResults] = useState<CaptureConfirmResult[]>([]);
  const [retryAction, setRetryAction] = useState<RetryAction>(null);

  const attachmentUrl = useMemo(() => {
    const value = attachmentInput.trim();
    return looksLikeUrl(value) ? value : undefined;
  }, [attachmentInput]);

  function onFileChange(file: File | null) {
    setError(null);
    if (!file) {
      setFileName(null);
      setFileType(null);
      return;
    }
    const rejected = attachmentError(file);
    if (rejected) {
      setFileName(null);
      setFileType(null);
      setError(rejected);
      return;
    }
    setFileName(file.name);
    setFileType(file.type || null);
    // Local personal use: treat filename/type as the attachment signal.
    // Binary upload to Social API media endpoint remains a follow-up.
    if (!attachmentInput.trim()) {
      setAttachmentInput(file.name);
    }
  }

  function toggleChannel(channel: string) {
    setSelected((current) =>
      current.includes(channel)
        ? current.filter((id) => id !== channel)
        : [...current, channel],
    );
  }

  async function handleSuggest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (attachmentInput.trim() && !attachmentUrl && !fileName) {
      setError('Attachment link must start with http:// or https://.');
      return;
    }
    if (!live) {
      setError('Holus backend is unavailable from this surface. No request was sent.');
      return;
    }
    setBusy(true);
    setRetryAction(null);
    setError(null);
    try {
      const response = await suggestCapture({
        text,
        attachment_url: attachmentUrl,
        attachment_filename: fileName ?? (attachmentUrl ? undefined : attachmentInput || undefined),
        attachment_content_type: fileType ?? undefined,
      });
      setSuggestions(response.suggestions);
      setSelected(response.suggestions.map((item) => item.channel));
      setDeliveryGranted(response.personal_delivery_granted);
      setSocialReachable(response.social_api_reachable);
      setStep('suggest');
    } catch (err) {
      setError(friendlyError(err));
      setRetryAction('suggest');
    } finally {
      setBusy(false);
    }
  }

  async function handlePreview() {
    if (selected.length === 0) {
      setError('Select at least one suggested destination.');
      return;
    }
    setBusy(true);
    setRetryAction(null);
    setError(null);
    try {
      const response = await previewCapture({
        text: text.trim() || attachmentInput.trim(),
        channels: selected,
        source_url: attachmentUrl,
      });
      setPreviews(response.previews);
      setStep('preview');
    } catch (err) {
      setError(friendlyError(err));
      setRetryAction('preview');
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm() {
    setBusy(true);
    setRetryAction(null);
    setError(null);
    try {
      const response = await confirmCapture({
        piece_ids: previews.map((item) => item.id),
        dry_run: false,
      });
      setConfirmResults(response.results);
      setDeliveryGranted(response.personal_delivery_granted);
      setStep('done');
      router.refresh();
    } catch (err) {
      setError(friendlyError(err));
      setRetryAction('confirm');
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setText('');
    setAttachmentInput('');
    setFileName(null);
    setFileType(null);
    setSuggestions([]);
    setSelected([]);
    setPreviews([]);
    setConfirmResults([]);
    setStep('capture');
    setError(null);
    setRetryAction(null);
  }

  function retry() {
    if (retryAction === 'suggest') void handleSuggest({ preventDefault: () => undefined } as FormEvent<HTMLFormElement>);
    if (retryAction === 'preview') void handlePreview();
    if (retryAction === 'confirm') void handleConfirm();
  }

  const canSuggest =
    live &&
    !busy &&
    (text.trim().length >= 3 || attachmentInput.trim().length > 0 || !!fileName);

  return (
    <section
      className="rounded-2xl overflow-hidden animate-fade-in shadow-sm"
      style={{
        border: '1px solid var(--border-default)',
        background: 'var(--surface-raised)',
      }}
    >
      <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p
              className="text-xs font-semibold uppercase tracking-[0.12em]"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Capture and share
            </p>
            <h2 className="text-xl font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
              One box. Suggest routes. Preview. Then post.
            </h2>
            {!live && (
              <p role="status" className="text-xs mt-2" style={{ color: 'var(--warning)' }}>
                {connection.label} - Holus backend unavailable here. Live capture is not sent.
              </p>
            )}
          </div>
          <span
            className="text-xs px-2 py-1 rounded font-medium"
            style={{
              background: 'var(--brand-subtle)',
              color: 'var(--brand)',
              border: '1px solid var(--border-default)',
            }}
          >
            {step === 'capture' && '1 · Capture'}
            {step === 'suggest' && '2 · Suggest'}
            {step === 'preview' && '3 · Preview'}
            {step === 'done' && 'Done'}
          </span>
        </div>
      </div>

      <div className="p-6 space-y-5" aria-busy={busy}>
        {step === 'capture' && (
          <form onSubmit={handleSuggest} className="space-y-4" aria-label="Capture thought">
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={5}
              placeholder="Paste a thought, note, or draft…"
              className="w-full rounded-xl px-4 py-3 text-base resize-y focus-ring"
              style={{
                border: '1px solid var(--border-default)',
                background: '#ffffff',
                color: 'var(--text-primary)',
              }}
            />

            <div
              className="rounded-xl px-4 py-3 space-y-3"
              style={{
                border: '1px dashed var(--border-default)',
                background: 'var(--surface-2)',
              }}
            >
              <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                <Paperclip size={16} />
                Attachment slot — image, link, or PDF
              </div>
              <div className="flex flex-col sm:flex-row gap-2">
                <label className="relative flex-1">
                  <Link2
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                  <input
                    value={attachmentInput}
                    onChange={(event) => setAttachmentInput(event.target.value)}
                    placeholder="https://… or leave blank and pick a file"
                    className="w-full rounded-lg pl-9 pr-3 py-2 text-sm focus-ring"
                    style={{
                      border: '1px solid var(--border-default)',
                      background: '#ffffff',
                      color: 'var(--text-primary)',
                    }}
                  />
                </label>
                <label
                  className="inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium cursor-pointer focus-ring"
                  style={{
                    border: '1px solid var(--border-default)',
                    background: 'var(--surface-raised)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  Choose file
                  <input
                    type="file"
                    accept="image/*,application/pdf,.pdf"
                    className="sr-only"
                    onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
              {fileName && (
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  File: {fileName}
                  {fileType ? ` (${fileType})` : ''}
                </p>
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!canSuggest}
                className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-opacity disabled:opacity-40 focus-ring"
                style={{
                  background: 'var(--button-approve-bg)',
                  color: 'var(--text-inverse)',
                }}
              >
                <Sparkles size={15} />
                {busy ? 'Checking capture…' : 'Suggest destinations'}
              </button>
            </div>
          </form>
        )}

        {step === 'suggest' && (
          <div className="space-y-4">
            <p className="text-sm" aria-live="polite" style={{ color: 'var(--text-secondary)' }}>
              {busy ? 'Loading route suggestions…' : 'Suggested routes'}
              {socialReachable === false && ' · Social API not reachable from this host'}
              {socialReachable === true && ' · Social API reachable'}
              {deliveryGranted
                ? ' · personal delivery grant ON'
                : ' · delivery contained until grant + confirm'}
            </p>
            <div className="grid gap-2">
              {suggestions.map((item) => {
                const on = selected.includes(item.channel);
                return (
                  <button
                    key={item.channel}
                    type="button"
                    onClick={() => toggleChannel(item.channel)}
                    className="text-left rounded-xl px-4 py-3 focus-ring"
                    style={{
                      border: on ? '1px solid var(--brand)' : '1px solid var(--border-default)',
                      background: on ? 'var(--brand-subtle)' : 'var(--surface-2)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {item.platform} · {item.format_hint}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                      {item.edit_notes}
                    </p>
                    <p
                      className="text-xs mt-2 whitespace-pre-wrap"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      {item.preview_text}
                    </p>
                  </button>
                );
              })}
            </div>
            <div className="flex justify-between gap-3">
              <button
                type="button"
                onClick={() => setStep('capture')}
                className="text-sm font-medium focus-ring"
                style={{ color: 'var(--text-secondary)' }}
              >
                Back
              </button>
              <button
                type="button"
                disabled={busy || selected.length === 0}
                onClick={handlePreview}
                className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-40 focus-ring"
                style={{
                  background: 'var(--button-approve-bg)',
                  color: 'var(--text-inverse)',
                }}
              >
                {busy ? 'Building preview…' : 'Build preview'}
              </button>
            </div>
          </div>
        )}

        {step === 'preview' && (
          <div className="space-y-4">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Review drafts before anything leaves Holus.
            </p>
            <div className="grid gap-3">
              {previews.map((item) => (
                <article
                  key={item.id}
                  className="rounded-xl px-4 py-3"
                  style={{
                    border: '1px solid var(--border-default)',
                    background: 'var(--surface-2)',
                  }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {item.platform} · {item.content_type}
                    </h3>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {item.id}
                    </span>
                  </div>
                  <p
                    className="text-sm mt-2 whitespace-pre-wrap"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {item.text || item.title || '(empty draft)'}
                  </p>
                </article>
              ))}
            </div>
            <div className="flex justify-between gap-3">
              <button
                type="button"
                onClick={() => setStep('suggest')}
                className="text-sm font-medium focus-ring"
                style={{ color: 'var(--text-secondary)' }}
              >
                Back
              </button>
              <button
                type="button"
                disabled={busy || previews.length === 0}
                onClick={handleConfirm}
                className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-40 focus-ring"
                style={{
                  background: 'var(--button-approve-bg)',
                  color: 'var(--text-inverse)',
                }}
              >
                <Send size={15} />
                {busy ? 'Confirming…' : 'Confirm and post'}
              </button>
            </div>
          </div>
        )}

        {step === 'done' && (
          <div className="space-y-4">
            <div className="flex items-start gap-2">
              <CheckCircle2 size={18} style={{ color: 'var(--success)' }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Capture loop finished
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  {deliveryGranted
                    ? 'Personal delivery grant was on; Social API was asked to publish.'
                    : 'Delivery stayed contained (outbox intent recorded). Set HOLUS_PERSONAL_DELIVERY_GRANT=1 with a live Social API to post for real.'}
                </p>
              </div>
            </div>
            <ul className="space-y-2">
              {confirmResults.map((result) => (
                <li
                  key={result.piece_id}
                  className="rounded-lg px-3 py-2 text-sm"
                  style={{
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {result.piece_id}: {result.status}
                  {result.publish_id ? ` · ${result.publish_id}` : ''}
                  {result.detail ? ` · ${result.detail}` : ''}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={reset}
              className="text-sm font-medium focus-ring"
              style={{ color: 'var(--brand)' }}
            >
              Capture another
            </button>
          </div>
        )}

        {error && (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--danger)' }}>
            <span className="inline-flex items-center gap-1.5">
              <AlertCircle size={14} />
              {error}
            </span>
            {retryAction && (
              <button type="button" onClick={retry} disabled={busy} className="font-semibold underline focus-ring">
                Try again
              </button>
            )}
            <button type="button" onClick={reset} disabled={busy} className="font-semibold underline focus-ring">
              Start over
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
