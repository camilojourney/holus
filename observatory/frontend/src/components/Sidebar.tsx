'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import {
  Info,
  BarChart3,
  UserPlus,
  LayoutDashboard,
  Users,
  FileText,
  Target,
  BookOpen,
  Activity,
  TrendingUp,
  Menu,
  X,
  Sun,
  Moon,
} from 'lucide-react';
import HolusLogo from '@/components/HolusLogo';

const nav = [
  { href: '/about', label: 'Architecture', Icon: Info, section: null },
  { href: '/', label: 'Inference Feed', Icon: LayoutDashboard, section: null },
  { href: '/agents', label: 'Agent Fleet', Icon: Users, section: 'system' },
  { href: '/content', label: 'Content Pipeline', Icon: FileText, section: 'system' },
  { href: '/evaluations', label: 'Quality Signals', Icon: Target, section: 'system' },
  { href: '/engagement', label: 'Engagement', Icon: BarChart3, section: 'signals' },
  { href: '/followers', label: 'Audience Growth', Icon: UserPlus, section: 'signals' },
  { href: '/results', label: 'Performance', Icon: TrendingUp, section: 'signals' },
  { href: '/knowledge', label: 'Knowledge Graph', Icon: BookOpen, section: 'ops' },
  { href: '/health', label: 'System Diagnostics', Icon: Activity, section: 'ops' },
];

const sectionLabels: Record<string, string> = {
  system: 'Orchestration',
  signals: 'Market Signals',
  ops: 'Operations',
};

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('theme');
    if (stored === 'light') {
      setDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  }

  let lastSection: string | null = null;

  const sidebarContent = (
    <>
      {/* Brand header */}
      <div className="px-5 py-5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-default)' }}>
        <div className="flex items-center gap-2.5">
          {/* Brand mark */}
          <HolusLogo size={32} />
          <div>
            <div className="text-[0.65rem] font-semibold tracking-[0.15em] uppercase" style={{ color: 'var(--text-tertiary)' }}>
              Holus
            </div>
            <div className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Observatory
            </div>
          </div>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="md:hidden p-1.5 rounded-lg focus-ring"
          style={{ color: 'var(--text-tertiary)' }}
          aria-label="Close navigation"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation */}
      <nav aria-label="Main navigation" className="flex-1 px-3 py-3 overflow-y-auto">
        {nav.map(({ href, label, Icon, section }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          const showSectionHeader = section !== null && section !== lastSection;
          lastSection = section;

          return (
            <div key={href}>
              {showSectionHeader && (
                <p
                  className="text-[0.625rem] font-semibold uppercase tracking-[0.12em] mt-5 mb-2 px-3"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {sectionLabels[section]}
                </p>
              )}
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
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = 'var(--surface-2)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <Icon size={16} aria-hidden="true" />
                {label}
              </Link>
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 flex items-center justify-between" style={{ borderTop: '1px solid var(--border-default)' }}>
        <p className="text-[0.6875rem]" style={{ color: 'var(--text-tertiary)' }}>Read-only</p>
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg transition-colors focus-ring"
          style={{ color: 'var(--text-tertiary)' }}
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed top-4 left-4 z-40 md:hidden p-2 rounded-lg shadow-sm focus-ring"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-secondary)',
        }}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 md:hidden backdrop-blur-sm"
          style={{ background: 'var(--surface-overlay)' }}
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile slide-over sidebar */}
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

      {/* Desktop sidebar */}
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
