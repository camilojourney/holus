'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import ConnectionStatus from '@/components/ConnectionStatus';
import { resolveConnection } from '@/lib/connection';
import { DEMO_REQUEST, type GenerationJobStatus, type PublicGenerationStatus } from '@/lib/generation/contract';
import { DemoGenerationAdapter } from '@/lib/generation/demo-adapter';

const STAGES: PublicGenerationStatus[] = ['queued', 'generating', 'ready', 'error'];

interface Props {
  variant?: 'page' | 'teaser';
}

function StageRail({ current }: { current: PublicGenerationStatus | null }) {
  return (
    <ol className="generation-rail" aria-label="Demonstration lifecycle">
      {STAGES.map((stage) => {
        const reached =
          current !== null &&
          (STAGES.indexOf(current) >= STAGES.indexOf(stage) ||
            (current === 'error' && (stage === 'queued' || stage === 'generating' || stage === 'error')));
        const isCurrent = current === stage;
        const skippedReady = current === 'error' && stage === 'ready';
        return (
          <li
            key={stage}
            data-stage={stage}
            data-current={isCurrent ? 'true' : 'false'}
            className="generation-stage"
            style={{
              opacity: skippedReady ? 0.35 : 1,
              borderColor: isCurrent ? 'var(--brand)' : 'var(--border-default)',
              background: isCurrent ? 'var(--brand-subtle)' : 'var(--surface-1)',
              color: reached && !skippedReady ? 'var(--text-primary)' : 'var(--text-tertiary)',
            }}
          >
            <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em]">{stage}</span>
          </li>
        );
      })}
    </ol>
  );
}

function PreviewPane({ status }: { status: GenerationJobStatus | null }) {
  if (!status || status.preview.availability === 'unavailable') {
    return (
      <div
        className="rounded-xl min-h-40 flex items-center justify-center px-4 text-center"
        style={{
          border: '1px dashed var(--border-strong)',
          background: 'var(--surface-2)',
          color: 'var(--text-secondary)',
        }}
      >
        <p className="text-sm">
          {status?.preview.label ?? 'Preview unavailable until the demonstration reaches a terminal state.'}
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl min-h-40 px-5 py-6"
      style={{
        border: '1px solid var(--border-default)',
        background: 'linear-gradient(180deg, var(--brand-subtle), var(--surface-raised))',
      }}
    >
      <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16em]" style={{ color: 'var(--brand)' }}>
        Local placeholder
      </p>
      <p className="text-lg font-semibold mt-2" style={{ color: 'var(--text-primary)' }}>
        Representative output
      </p>
      <p className="text-sm mt-2 leading-6" style={{ color: 'var(--text-secondary)' }}>
        {status.preview.label}. This is demonstration state, not a generated artifact or storage URL.
      </p>
    </div>
  );
}

export default function GenerationStudio({ variant = 'page' }: Props) {
  const connection = useMemo(() => resolveConnection(), []);
  const adapterRef = useRef<DemoGenerationAdapter | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<GenerationJobStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    adapterRef.current = new DemoGenerationAdapter({ intervalMs: variant === 'teaser' ? 550 : 700 });
    return () => {
      unsubscribeRef.current?.();
      adapterRef.current?.dispose();
    };
  }, [variant]);

  function run(outcome: 'ready' | 'error') {
    unsubscribeRef.current?.();
    const adapter = adapterRef.current;
    if (!adapter) return;
    const created = adapter.create(DEMO_REQUEST, outcome);
    const initial = adapter.get(created.request_id) ?? null;
    setStatus(initial);
    setBusy(true);
    unsubscribeRef.current = adapter.subscribe(created.request_id, (next) => {
      setStatus(next);
      if (next.status === 'ready' || next.status === 'error') setBusy(false);
    });
  }

  return (
    <section
      aria-labelledby="generation-demo-heading"
      className="rounded-2xl p-6 space-y-5"
      style={{
        border: '1px solid var(--border-default)',
        background: 'var(--surface-raised)',
      }}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[0.65rem] font-semibold tracking-[0.16em] uppercase" style={{ color: 'var(--brand)' }}>
            Private generation capability
          </p>
          <h2
            id="generation-demo-heading"
            className={variant === 'teaser' ? 'text-xl font-bold mt-1' : 'text-2xl font-bold mt-1'}
            style={{ color: 'var(--text-primary)' }}
          >
            Holus-orchestrated generation demo
          </h2>
          <p className="text-sm mt-2 max-w-2xl leading-6" style={{ color: 'var(--text-secondary)' }}>
            Genpeli remains a private generation system. This interaction runs only on a local Holus adapter.
            No live job is created, and no external generation endpoint is called.
          </p>
        </div>
        <ConnectionStatus state={connection} />
      </div>

      <div
        className="rounded-xl px-4 py-3 text-sm"
        style={{ background: 'var(--warning-subtle)', color: 'var(--warning)' }}
      >
        Safe demo — generation connection is unavailable. An authenticated Holus BFF is not connected.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] gap-5">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
              Demonstration request
            </p>
            <p className="text-sm leading-6" style={{ color: 'var(--text-primary)' }}>
              {DEMO_REQUEST.instruction}
            </p>
            <p className="text-xs mt-2 font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {DEMO_REQUEST.niche} · {DEMO_REQUEST.target_platform} · {DEMO_REQUEST.mode}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => run('ready')}
              disabled={busy}
              className="px-4 py-2.5 rounded-lg text-sm font-semibold focus-ring disabled:opacity-60"
              style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
            >
              Run demonstration
            </button>
            <button
              type="button"
              onClick={() => run('error')}
              disabled={busy}
              className="px-4 py-2.5 rounded-lg text-sm font-medium focus-ring disabled:opacity-60"
              style={{
                border: '1px solid var(--border-default)',
                color: 'var(--text-secondary)',
              }}
            >
              Demonstrate error
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <StageRail current={status?.status ?? null} />
          <dl className="grid grid-cols-1 gap-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt style={{ color: 'var(--text-tertiary)' }}>Request</dt>
              <dd className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>
                {status?.request_id ?? '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt style={{ color: 'var(--text-tertiary)' }}>Mapped job</dt>
              <dd className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>
                {status?.job_id ?? '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt style={{ color: 'var(--text-tertiary)' }}>Stage</dt>
              <dd style={{ color: 'var(--text-primary)' }}>{status?.stage ?? 'idle'}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt style={{ color: 'var(--text-tertiary)' }}>Progress</dt>
              <dd className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>
                {status?.progress == null ? '—' : `${Math.round(status.progress * 100)}%`}
              </dd>
            </div>
          </dl>
          {status?.user_message && (
            <p className="text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
              {status.user_message}
            </p>
          )}
        </div>
      </div>

      <PreviewPane status={status} />
    </section>
  );
}
