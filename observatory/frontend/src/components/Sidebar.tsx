'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  Users,
  FileText,
  Target,
  BookOpen,
  Activity,
  Menu,
  X,
  Sun,
  Moon,
} from 'lucide-react';

const nav = [
  { href: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { href: '/agents', label: 'Agents', Icon: Users },
  { href: '/content', label: 'Content', Icon: FileText },
  { href: '/evaluations', label: 'Evaluations', Icon: Target },
  { href: '/knowledge', label: 'Knowledge', Icon: BookOpen },
  { href: '/health', label: 'Health', Icon: Activity },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(true);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
  }

  const sidebarContent = (
    <>
      <div className="px-5 py-5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase">
            Holus
          </span>
          <div className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
            Observatory
          </div>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="md:hidden p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Close navigation"
        >
          <X size={20} />
        </button>
      </div>
      <nav aria-label="Main navigation" className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <p className="text-xs text-gray-400 dark:text-gray-600">Read-only</p>
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg text-gray-400 dark:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
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
        className="fixed top-4 left-4 z-40 md:hidden p-2 rounded-lg bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 shadow-sm"
        aria-label="Open navigation"
      >
        <Menu size={20} className="text-gray-700 dark:text-gray-300" />
      </button>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile slide-over sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-56 bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 flex flex-col transform transition-transform md:hidden ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex-col">
        {sidebarContent}
      </aside>
    </>
  );
}
