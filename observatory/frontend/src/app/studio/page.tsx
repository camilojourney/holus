'use client';

import Link from 'next/link';
import GenerationStudio from '@/components/GenerationStudio';
import ExploreApiLink from '@/components/ExploreApiLink';

export default function StudioPage() {
  return (
    <div className="page-transition">
      <div className="mx-auto max-w-5xl space-y-8" style={{ padding: 'var(--page-padding)' }}>
        <header className="space-y-3 pt-2">
          <p className="text-[0.65rem] font-semibold tracking-[0.18em] uppercase" style={{ color: 'var(--brand)' }}>
            Generation studio
          </p>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            A bounded Holus generation request.
          </h1>
          <p className="text-sm sm:text-base max-w-2xl leading-7" style={{ color: 'var(--text-secondary)' }}>
            Use the labelled demonstration to walk queued, generating, ready, and error states.
            Holus owns this presentation. Genpeli is not called from the browser.
          </p>
          <Link href="/" className="inline-flex text-sm font-medium focus-ring" style={{ color: 'var(--brand)' }}>
            Back to Holus overview
          </Link>
        </header>
        <GenerationStudio variant="page" />
        <ExploreApiLink variant="panel" />
      </div>
    </div>
  );
}
