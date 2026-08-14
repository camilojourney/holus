'use client';

import { SOCIAL_API_CAPABILITY, SOCIAL_API_OPENAPI, SOCIAL_API_ORIGIN } from '@/lib/generation/contract';

interface Props {
  variant?: 'button' | 'secondary' | 'inline' | 'panel';
}

export default function ExploreApiLink({ variant = 'button' }: Props) {
  if (variant === 'inline') {
    return (
      <a
        href={SOCIAL_API_ORIGIN}
        className="font-medium underline-offset-4 hover:underline focus-ring"
        style={{ color: 'var(--brand)' }}
      >
        Explore the API
      </a>
    );
  }

  if (variant === 'panel') {
    return (
      <section
        aria-labelledby="explore-api-heading"
        className="rounded-2xl p-6"
        style={{
          border: '1px solid var(--border-default)',
          background: 'var(--surface-raised)',
        }}
      >
        <p
          className="text-[0.65rem] font-semibold tracking-[0.16em] uppercase"
          style={{ color: 'var(--brand)' }}
        >
          Social content API
        </p>
        <h2
          id="explore-api-heading"
          className="text-2xl font-bold mt-2 tracking-tight"
          style={{ color: 'var(--text-primary)' }}
        >
          Integrate from one contract.
        </h2>
        <p className="text-sm mt-3 leading-6 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
          {SOCIAL_API_CAPABILITY}
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <a
            href={SOCIAL_API_ORIGIN}
            className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-semibold focus-ring"
            style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
          >
            Explore the API
          </a>
          <a
            href={SOCIAL_API_OPENAPI}
            className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-medium focus-ring"
            style={{
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
            }}
          >
            OpenAPI contract
          </a>
        </div>
        <p className="text-xs mt-4" style={{ color: 'var(--text-tertiary)' }}>
          Authenticated server-side use only. This page does not publish, store keys, or run admin or OAuth flows.
        </p>
      </section>
    );
  }

  const isSecondary = variant === 'secondary';
  return (
    <a
      href={SOCIAL_API_ORIGIN}
      className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-semibold focus-ring"
      style={isSecondary
        ? { border: '1px solid var(--border-default)', color: 'var(--text-primary)' }
        : { background: 'var(--brand)', color: 'var(--text-inverse)' }}
    >
      Explore the API
    </a>
  );
}
