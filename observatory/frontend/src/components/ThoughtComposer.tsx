'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Send, CheckCircle2, AlertCircle, FileText, Image as ImageIcon, MessageSquare, PanelsTopLeft } from 'lucide-react';
import { createContentFromThought } from '@/lib/api';

const platforms = [
  { id: 'linkedin_text', label: 'LinkedIn Post', format: 'Authority copy', icon: FileText },
  { id: 'linkedin_carousel', label: 'LinkedIn Carousel', format: 'Document carousel', icon: PanelsTopLeft },
  { id: 'instagram_image', label: 'Instagram Image', format: 'Visual asset', icon: ImageIcon },
  { id: 'instagram_carousel', label: 'Instagram Carousel', format: 'Slide sequence', icon: PanelsTopLeft },
  { id: 'threads_text', label: 'Threads Post', format: 'Conversation copy', icon: MessageSquare },
  { id: 'twitter_x_thread', label: 'X Thread', format: 'Thread outline', icon: FileText },
  { id: 'facebook_text', label: 'Facebook Post', format: 'Community post', icon: MessageSquare },
];

export default function ThoughtComposer() {
  const router = useRouter();
  const [thought, setThought] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState(platforms.map((platform) => platform.id));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function togglePlatform(platformId: string) {
    setSelectedPlatforms((current) =>
      current.includes(platformId)
        ? current.filter((id) => id !== platformId)
        : [...current, platformId],
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await createContentFromThought({
        thought,
        platforms: selectedPlatforms,
      });
      setThought('');
      setResult(`${response.items.length} drafts queued for review`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = thought.trim().length >= 8 && selectedPlatforms.length > 0 && !busy;

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl overflow-hidden animate-fade-in shadow-sm"
      style={{
        border: '1px solid var(--border-default)',
        background: 'var(--surface-raised)',
      }}
    >
      <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: 'var(--text-tertiary)' }}>
              Start here
            </p>
            <h2 className="text-xl font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
              What thought should Holus turn into content?
            </h2>
          </div>
          <span
            className="text-xs px-2 py-1 rounded font-medium"
            style={{
              background: 'var(--warning-subtle)',
              color: 'var(--warning)',
              border: '1px solid #fed7aa',
            }}
          >
            Review gate
          </span>
        </div>
      </div>

      <div className="p-6 space-y-5">
        <textarea
          value={thought}
          onChange={(event) => setThought(event.target.value)}
          rows={5}
          placeholder="Example: The best AI systems do not start with agents. They start with a sharp content loop: thought, format, review, schedule, learn."
          className="w-full rounded-xl px-4 py-3 text-base resize-y focus-ring"
          style={{
            border: '1px solid var(--border-default)',
            background: '#ffffff',
            color: 'var(--text-primary)',
            boxShadow: 'inset 0 1px 2px rgba(15, 23, 42, 0.04)',
          }}
        />

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: 'var(--text-tertiary)' }}>
            Formats to create
          </p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {selectedPlatforms.length}/{platforms.length} selected
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
          {platforms.map((platform) => {
            const selected = selectedPlatforms.includes(platform.id);
            const Icon = platform.icon;
            return (
              <button
                key={platform.id}
                type="button"
                onClick={() => togglePlatform(platform.id)}
                className="text-left rounded-xl px-3 py-2.5 focus-ring transition-colors"
                style={{
                  border: selected ? '1px solid var(--brand)' : '1px solid var(--border-default)',
                  background: selected ? 'var(--brand-subtle)' : 'var(--surface-2)',
                  color: selected ? 'var(--brand)' : 'var(--text-secondary)',
                }}
              >
                <span className="flex items-start gap-2">
                  <Icon size={16} className="mt-0.5 shrink-0" />
                  <span>
                    <span className="block text-sm font-semibold">{platform.label}</span>
                    <span className="block text-xs mt-0.5" style={{ color: selected ? 'var(--brand)' : 'var(--text-tertiary)' }}>
                      {platform.format}
                    </span>
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="min-h-5">
            {result && (
              <p className="inline-flex items-center gap-1.5 text-xs" style={{ color: 'var(--success)' }}>
                <CheckCircle2 size={14} />
                {result}
              </p>
            )}
            {error && (
              <p className="inline-flex items-center gap-1.5 text-xs" style={{ color: 'var(--danger)' }}>
                <AlertCircle size={14} />
                {error}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-opacity disabled:opacity-40 focus-ring"
            style={{
              background: 'var(--button-approve-bg)',
              color: 'var(--text-inverse)',
              boxShadow: canSubmit ? '0 12px 24px rgba(79, 70, 229, 0.22)' : 'none',
            }}
          >
            <Send size={15} />
            {busy ? 'Generating...' : 'Generate content set'}
          </button>
        </div>
      </div>
    </form>
  );
}
