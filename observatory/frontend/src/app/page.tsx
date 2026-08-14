'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import ConnectionStatus from '@/components/ConnectionStatus';
import ExploreApiLink from '@/components/ExploreApiLink';
import GenerationStudio from '@/components/GenerationStudio';
import TrajectoryTimeline from '@/components/TrajectoryTimeline';
import { resolveConnection } from '@/lib/connection';

const story = [
  {
    n: '01',
    title: 'Holus orchestrates',
    body: 'Holus is the public product: identity, presentation, review, and the future authenticated backend. Generation is a private capability behind that layer, not a separate destination.',
  },
  {
    n: '02',
    title: 'Generation stays private',
    body: 'A Holus BFF may later create one mapped job, read its restricted status, and proxy a preview. This demo never contacts that service and never implies a live job exists.',
  },
  {
    n: '03',
    title: 'Progress is user-safe',
    body: 'Visitors see a request identifier, permitted stage, bounded progress, a user-facing error state, and Holus connection status. Costs, traces, artifacts, and operator controls stay out of the public contract.',
  },
];

export default function HomePage() {
  const connection = resolveConnection();

  return (
    <div className="page-transition">
      <div className="mx-auto max-w-5xl space-y-16" style={{ padding: 'var(--page-padding)' }}>
        <header className="space-y-6 pt-4 md:pt-10">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-[0.65rem] font-semibold tracking-[0.18em] uppercase" style={{ color: 'var(--brand)' }}>
              Holus
            </p>
            <ConnectionStatus state={connection} />
          </div>
          <h1
            className="text-4xl sm:text-5xl font-extrabold tracking-tight max-w-3xl leading-[1.1]"
            style={{ color: 'var(--text-primary)' }}
          >
            Orchestration for AI content, with honest generation progress.
          </h1>
          <p className="text-lg max-w-2xl leading-8" style={{ color: 'var(--text-secondary)' }}>
            Holus is the single public product. It turns a thought into platform-native content,
            shows only user-safe job state, and publishes through a versioned social-content API.
            Genpeli remains a private generation capability — not a public app to open.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/studio"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold focus-ring"
              style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
            >
              Run a generation demo <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <ExploreApiLink variant="secondary" />
            <Link
              href="/health"
              className="inline-flex items-center px-4 py-2.5 rounded-lg text-sm font-medium focus-ring"
              style={{ border: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}
            >
              Reliability
            </Link>
          </div>
        </header>

        <ol className="space-y-6">
          {story.map((item) => (
            <li key={item.n} className="grid grid-cols-[auto_minmax(0,1fr)] gap-4 sm:gap-6">
              <span className="font-mono text-sm pt-1" style={{ color: 'var(--brand)' }}>
                {item.n}
              </span>
              <div>
                <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {item.title}
                </h2>
                <p className="text-sm mt-2 leading-7 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
                  {item.body}
                </p>
              </div>
            </li>
          ))}
        </ol>

        <GenerationStudio variant="teaser" />

        <section aria-labelledby="progress-heading" className="space-y-4">
          <div>
            <h2 id="progress-heading" className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Honest agent progress
            </h2>
            <p className="text-sm mt-2 max-w-2xl leading-7" style={{ color: 'var(--text-secondary)' }}>
              Live inference events are not available on this public surface. The stream below
              states that an authenticated backend connection is required. It does not connect to localhost.
            </p>
          </div>
          <TrajectoryTimeline />
        </section>

        <section aria-labelledby="output-heading" className="space-y-4">
          <h2 id="output-heading" className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Representative output
          </h2>
          <p className="text-sm max-w-2xl leading-7" style={{ color: 'var(--text-secondary)' }}>
            Content Studio shows Holus-owned drafts for review. Generation previews in this demo
            are local placeholders, never artifact URLs.
          </p>
          <Link
            href="/content"
            className="inline-flex items-center gap-2 text-sm font-medium focus-ring"
            style={{ color: 'var(--brand)' }}
          >
            Open Content Studio <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </section>

        <section
          aria-labelledby="reliability-heading"
          className="rounded-2xl p-6"
          style={{ border: '1px solid var(--border-default)', background: 'var(--surface-raised)' }}
        >
          <h2 id="reliability-heading" className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Reliability
          </h2>
          <p className="text-sm mt-2 max-w-2xl leading-7" style={{ color: 'var(--text-secondary)' }}>
            {connection.detail} This is not production telemetry, cost, latency, or external system health.
          </p>
          <Link
            href="/health"
            className="inline-flex items-center gap-2 mt-4 text-sm font-medium focus-ring"
            style={{ color: 'var(--brand)' }}
          >
            View connection status <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </section>

        <ExploreApiLink variant="panel" />
      </div>
    </div>
  );
}
