'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const nav = [
  { href: '/', label: 'Dashboard', icon: '▦' },
  { href: '/agents', label: 'Agents', icon: '◈' },
  { href: '/content', label: 'Content', icon: '◰' },
  { href: '/evaluations', label: 'Evaluations', icon: '◎' },
  { href: '/knowledge', label: 'Knowledge', icon: '◻' },
  { href: '/health', label: 'Health', icon: '◉' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex flex-col">
      <div className="px-5 py-5 border-b border-gray-200 dark:border-gray-800">
        <span className="text-sm font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase">
          Holus
        </span>
        <div className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
          Observatory
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <span className="text-base">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-800">
        <p className="text-xs text-gray-400 dark:text-gray-600">Read-only · Internal</p>
      </div>
    </aside>
  );
}
