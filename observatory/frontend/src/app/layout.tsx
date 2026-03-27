import type { Metadata } from 'next';
import { Plus_Jakarta_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';

const plusJakarta = Plus_Jakarta_Sans({
  variable: '--font-plus-jakarta',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Holus Observatory',
  description: 'Real-time inference monitoring for Holus -- a 32-agent federated AI system with domain-expert quality judges and self-improvement loops.',
  metadataBase: new URL('https://holus.camilomartinez.co'),
  openGraph: {
    title: 'Holus Observatory',
    description: 'Real-time inference monitoring for a 32-agent federated AI system with quality judges and self-improvement loops.',
    siteName: 'Holus Observatory',
    locale: 'en_US',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Holus Observatory -- Multi-Agent Inference Monitor',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Holus Observatory',
    description: 'Real-time inference monitoring for a 32-agent federated AI system with quality judges and self-improvement loops.',
    images: ['/og-image.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${plusJakarta.variable} ${jetbrainsMono.variable} antialiased min-h-screen`}
        style={{ background: 'var(--surface-0)', color: 'var(--text-primary)' }}
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[60] focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:rounded-lg focus:text-sm focus:font-medium focus:outline-none focus:ring-2 focus:ring-offset-2"
          style={{ background: 'var(--brand)', color: 'var(--text-inverse)' }}
        >
          Skip to content
        </a>
        <div className="flex min-h-screen">
          <Sidebar />
          <main id="main-content" className="flex-1 min-w-0 overflow-auto pt-14 md:pt-0">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
