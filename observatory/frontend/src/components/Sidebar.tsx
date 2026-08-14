'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  FileText,
  HeartPulse,
  Menu,
  X,
  Sun,
  Moon,
  Clapperboard,
  Compass,
  ExternalLink,
} from 'lucide-react';
import HolusLogo from '@/components/HolusLogo';
import ConnectionStatus from '@/components/ConnectionStatus';
import { SOCIAL_API_ORIGIN } from '@/lib/generation/contract';

const nav = [
  { href: '/', label: 'Overview', Icon: Compass, exact: true },
  { href: '/studio', label: 'Generation', Icon: Clapperboard },
  { href: '/content', label: 'Content', Icon: FileText },
  { href: '/health', label: 'Health', Icon: HeartPulse },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(
    () => typeof window === 'undefined' || localStorage.getItem('theme') !== 'light',
  );

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  }

  const sidebarContent = (
    <>
      <div className="px-5 py-5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-default)' }}>
        <Link href="/" className="flex items-center gap-2.5 focus-ring rounded-lg" onClick={() => setOpen(false)}>
          <HolusLogo size={32} />
          <div>
            <div className="text-[0.65rem] font-semibold tracking-[0.15em] uppercase" style={{ color: 'var(--text-tertiary)' }}>
              Holus
            </div>
            <div className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Product
            </div>
          </div>
        </Link>
        <button
          onClick={() => setOpen(false)}
          className="md:hidden p-1.5 rounded-lg focus-ring"
          style={{ color: 'var(--text-tertiary)' }}
          aria-label="Close navigation"
        >
          <X size={20} />
        </button>
      </div>

      <nav aria-label="Main navigation" className="flex-1 px-3 py-3 overflow-y-auto">
        {nav.map(({ href, label, Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);

          return (
            <div key={href}>
              <Link
                href={href}
                aria-current={active ? 'page' : undefined}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[0.8125rem] font-medium nav-link focus-ring ${
                  active ? 'shadow-sm' : ''
                }`}
                style={{
                  background: active ? 'var(--brand-subtle)' : 'transparent',
                  color: active ? 'var(--brand)' : 'var(--text-secondary)',
                  borderLeft: active ? '3px solid var(--brand)' : '3px solid transparent',
                }}
              >
                <Icon size={16} aria-hidden="true" />
                {label}
              </Link>
            </div>
          );
        })}
        <a
          href={SOCIAL_API_ORIGIN}
          className="mt-2 flex items-center gap-2.5 px-3 py-2 rounded-lg text-[0.8125rem] font-medium nav-link focus-ring"
          style={{ color: 'var(--text-secondary)', borderLeft: '3px solid transparent' }}
        >
          <ExternalLink size={16} aria-hidden="true" />
          Explore the API
        </a>
      </nav>

      <div className="px-5 py-3 space-y-3" style={{ borderTop: '1px solid var(--border-default)' }}>
        <ConnectionStatus />
        <div className="flex items-center justify-between">
          <p className="text-[0.6875rem]" style={{ color: 'var(--text-tertiary)' }}>
            Public demo
          </p>
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg transition-colors focus-ring"
            style={{ color: 'var(--text-tertiary)' }}
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed top-4 right-2 z-40 md:hidden p-2 rounded-lg shadow-sm focus-ring"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-secondary)',
        }}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 md:hidden backdrop-blur-sm"
          style={{ background: 'var(--surface-overlay)' }}
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-56 flex flex-col transform transition-transform md:hidden ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{
          background: 'var(--surface-raised)',
          borderRight: '1px solid var(--border-default)',
        }}
      >
        {sidebarContent}
      </aside>

      <aside
        className="hidden md:flex w-56 shrink-0 flex-col"
        style={{
          background: 'var(--surface-raised)',
          borderRight: '1px solid var(--border-default)',
        }}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
