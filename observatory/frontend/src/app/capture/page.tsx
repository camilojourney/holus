'use client';

import Link from 'next/link';
import CaptureShare from '@/components/CaptureShare';

export default function CapturePage() {
  return (
    <div className="page-transition">
      <div className="mx-auto max-w-3xl space-y-8" style={{ padding: 'var(--page-padding)' }}>
        <header className="space-y-3 pt-2">
          <p
            className="text-[0.65rem] font-semibold tracking-[0.18em] uppercase"
            style={{ color: 'var(--brand)' }}
          >
            Personal capture
          </p>
          <h1
            className="text-3xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            Capture once. Route everywhere Holus already connects.
          </h1>
          <p className="text-sm sm:text-base max-w-2xl leading-7" style={{ color: 'var(--text-secondary)' }}>
            Text plus an optional image, link, or PDF. Holus suggests destinations and formats,
            you preview, then confirm before the Social API posts.
          </p>
          <Link href="/content" className="inline-flex text-sm font-medium focus-ring" style={{ color: 'var(--brand)' }}>
            Open content queue
          </Link>
        </header>
        <CaptureShare />
      </div>
    </div>
  );
}
