'use client';

import Link from 'next/link';
import { Github, Linkedin, Globe } from 'lucide-react';
import ExploreApiLink from '@/components/ExploreApiLink';
import ConnectionStatus from '@/components/ConnectionStatus';

const loopSteps = [
  {
    title: 'Observe',
    description: 'Read performance snapshots from the Holus social-content API after authenticated publishing.',
  },
  {
    title: 'Reason',
    description: 'Plan platform-native content from a single thought without exposing operator internals.',
  },
  {
    title: 'Act',
    description: 'Dispatch Holus-owned generation and drafting. Private generation stays behind a future BFF.',
  },
  {
    title: 'Evaluate',
    description: 'Keep human review as the default gate before any schedule or publish action.',
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-12 page-transition" style={{ padding: 'var(--page-padding)' }}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-[0.65rem] font-semibold tracking-[0.18em] uppercase" style={{ color: 'var(--brand)' }}>
            Architecture
          </p>
          <ConnectionStatus />
        </div>
        <h1 className="text-4xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Holus
        </h1>
        <p className="text-lg max-w-2xl leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Holus is the orchestration layer for AI content. The public product lives at holus.camilomartinez.co.
          Generation is a private capability. Publishing is a versioned API for authenticated teams.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2.5 rounded-lg text-sm font-semibold focus-ring"
            style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
          >
            Product overview
          </Link>
          <Link
            href="/studio"
            className="inline-flex items-center px-4 py-2.5 rounded-lg text-sm font-medium focus-ring"
            style={{ border: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}
          >
            Generation demo
          </Link>
        </div>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {loopSteps.map((step) => (
          <div key={step.title} className="card">
            <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{step.title}</h2>
            <p className="text-sm mt-2 leading-6" style={{ color: 'var(--text-secondary)' }}>{step.description}</p>
          </div>
        ))}
      </section>

      <section className="card">
        <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Technical architecture</h2>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          The browser talks only to Holus. A future authenticated Holus BFF may initiate one mapped
          generation job, read that job&apos;s restricted status, and proxy a preview. Genpeli keeps
          generation, artifacts, review, delivery, and credentials. Holus never iframes or deep-links
          a separate generation site.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm mt-5">
          {[
            ['Public product', 'Holus'],
            ['Presentation', 'Next.js Observatory'],
            ['Future seam', 'Authenticated Holus BFF'],
            ['Generation', 'Private capability'],
            ['Publishing', 'Holus social-content API'],
            ['Contract', 'holus.generation.v1'],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{value}</p>
            </div>
          ))}
        </div>
      </section>

      <ExploreApiLink variant="panel" />

      <section style={{ borderTop: '1px solid var(--border-default)', paddingTop: '1.5rem' }}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Built by Juan Camilo Martinez
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              AI Engineer. MS Business Analytics, Baruch College.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {[
              { href: 'https://camilomartinez.co', label: 'Personal website', Icon: Globe },
              { href: 'https://linkedin.com/in/camilomartinez-ai', label: 'LinkedIn profile', Icon: Linkedin },
              { href: 'https://github.com/camilojourney', label: 'GitHub profile', Icon: Github },
            ].map(({ href, label, Icon }) => (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="p-2 rounded-lg transition-colors focus-ring"
                style={{ color: 'var(--text-tertiary)' }}
              >
                <Icon size={18} />
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
