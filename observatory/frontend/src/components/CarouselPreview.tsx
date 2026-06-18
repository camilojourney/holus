'use client';

import { useMemo, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import { contentPdfUrl } from '@/lib/api';
import type { ContentDetail } from '@/lib/types';

interface CarouselPreviewProps {
  detail?: ContentDetail;
  pieceId: string;
  label: string;
  maxSlides?: number;
}

interface SlidePreview {
  kicker: string;
  title: string;
  body: string;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => asString(item)).filter(Boolean)
    : [];
}

function slidesFromSpec(detail?: ContentDetail): SlidePreview[] {
  const spec = asRecord(detail?.visual_spec);
  const savedSlides = Array.isArray(spec.carousel_slides) ? spec.carousel_slides : [];
  if (savedSlides.length > 0) {
    return savedSlides.map((slide, index) => {
      const variables = asRecord(asRecord(slide).variables);
      const items = stringList(variables.items).join('\n');
      return {
        kicker: asString(asRecord(slide).type) || `Slide ${index + 1}`,
        title:
          asString(variables.headline) ||
          asString(variables.title) ||
          asString(variables.label) ||
          `Slide ${index + 1}`,
        body:
          asString(variables.subheadline) ||
          asString(variables.body) ||
          asString(variables.highlight) ||
          items,
      };
    });
  }

  const essence = asRecord(detail?.thought_essence);
  const creative = asRecord(spec.creative_contract);
  const rationale = asRecord(spec.variable_rationale);
  const roleMap = stringList(essence.role_map);
  const evidence = stringList(essence.evidence);
  const text = asString(detail?.text)
    .replace(/^Carousel caption\s*/i, '')
    .trim();

  return [
    {
      kicker: asString(asRecord(spec.style_profile).profile_id) || 'Carousel',
      title: asString(spec.cover_hook) || asString(essence.thesis) || labelFallback(detail),
      body: asString(spec.cover_subhook) || asString(creative.content_job),
    },
    {
      kicker: 'Role map',
      title: 'The roles',
      body: roleMap.slice(0, 4).join('\n') || asString(creative.proof_mechanism),
    },
    {
      kicker: 'Evidence',
      title: evidence.length > 0 ? 'Budget split' : 'The proof',
      body: evidence.slice(0, 5).join('   ') || asString(rationale.proof_points),
    },
    {
      kicker: 'Rule',
      title: asString(creative.hook_pattern) || 'Operating rule',
      body: asString(creative.rhythm) || asString(creative.reader_action),
    },
    {
      kicker: 'Save',
      title: asString(creative.cta_style) || 'Save the architecture',
      body: text,
    },
  ].filter((slide) => slide.title || slide.body);
}

function labelFallback(detail?: ContentDetail): string {
  return detail?.title || detail?.id || 'Carousel preview';
}

function exportLabel(detail?: ContentDetail): string {
  const platformExport = asString(asRecord(detail?.visual_spec).platform_export);
  if (platformExport === 'instagram_multi_image_carousel') return 'Download review PDF';
  return 'Download PDF';
}

function shortText(text: string, max = 95): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 3).trim()}...`;
}

function slideBackground(index: number): string {
  if (index === 0) return 'linear-gradient(135deg, #080d19 0%, #111827 66%, #38250b 100%)';
  return '#0f172a';
}

export default function CarouselPreview({
  detail,
  pieceId,
  label,
  maxSlides = 5,
}: CarouselPreviewProps) {
  const spec = asRecord(detail?.visual_spec);
  const slides = useMemo(() => slidesFromSpec(detail).slice(0, maxSlides), [detail, maxSlides]);
  const [activeIndex, setActiveIndex] = useState(0);
  const rawTotal = Number(spec.slides);
  const totalSlides = Number.isFinite(rawTotal) && rawTotal > 0 ? rawTotal : slides.length;
  const isInspector = maxSlides > 3 && slides.length > 1;
  const safeActiveIndex = Math.min(activeIndex, Math.max(0, slides.length - 1));
  const activeSlide = slides[safeActiveIndex] ?? slides[0];
  const previewCopy =
    totalSlides > slides.length
      ? `${slides.length === 1 ? 'Cover preview' : `${slides.length} previews`} · ${totalSlides} slides`
      : `${totalSlides} ${totalSlides === 1 ? 'slide' : 'slides'} from Holus outline`;

  const pdfUrl = contentPdfUrl(pieceId);

  return (
    <div
      className="overflow-hidden rounded-lg"
      style={{ border: '1px solid var(--border-default)', background: 'var(--surface-raised)' }}
    >
      <div
        className="flex items-center justify-between gap-3 px-3 py-2"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div>
          <p
            className="text-xs font-semibold uppercase tracking-[0.1em]"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Carousel preview
          </p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            {previewCopy}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold focus-ring rounded px-2 py-1"
            style={{ color: 'var(--brand)', background: 'var(--brand-subtle)' }}
          >
            <ExternalLink size={14} aria-hidden="true" />
            Open PDF
          </a>
          <a
            href={pdfUrl}
            download
            className="inline-flex items-center gap-1.5 text-xs font-semibold focus-ring rounded px-2 py-1"
            style={{ color: 'var(--text-secondary)', background: 'var(--surface-2)' }}
          >
            <Download size={14} aria-hidden="true" />
            {exportLabel(detail)}
          </a>
        </div>
      </div>

      {isInspector && activeSlide ? (
        <div className="p-4 space-y-4">
          <section
            aria-label={`${label} selected slide ${safeActiveIndex + 1}`}
            className="rounded-lg p-6 md:p-8"
            style={{
              background: slideBackground(safeActiveIndex),
              color: '#f8fafc',
              minHeight: '32rem',
              border: '1px solid rgba(148, 163, 184, 0.18)',
            }}
          >
            <div className="flex h-full min-h-[28rem] flex-col justify-between gap-8">
              <div>
                <p
                  className="text-xs font-bold uppercase"
                  style={{ color: '#f59e0b', letterSpacing: '0.12em' }}
                >
                  {String(safeActiveIndex + 1).padStart(2, '0')} {activeSlide.kicker}
                </p>
                <h4
                  className="mt-8 text-3xl font-bold leading-tight"
                  style={{ overflowWrap: 'anywhere', letterSpacing: 0 }}
                >
                  {activeSlide.title}
                </h4>
              </div>
              {activeSlide.body && (
                <p
                  className="whitespace-pre-line text-base leading-relaxed"
                  style={{ color: '#cbd5e1', overflowWrap: 'anywhere' }}
                >
                  {activeSlide.body}
                </p>
              )}
            </div>
          </section>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Slide {safeActiveIndex + 1} of {totalSlides}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveIndex((index) => Math.max(0, index - 1))}
                disabled={safeActiveIndex === 0}
                className="rounded px-3 py-1 text-xs font-semibold disabled:opacity-40 focus-ring"
                style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-default)' }}
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setActiveIndex((index) => Math.min(slides.length - 1, index + 1))}
                disabled={safeActiveIndex >= slides.length - 1}
                className="rounded px-3 py-1 text-xs font-semibold disabled:opacity-40 focus-ring"
                style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-default)' }}
              >
                Next
              </button>
            </div>
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1" aria-label={`${label} slide thumbnails`}>
            {slides.map((slide, index) => (
              <button
                type="button"
                key={`${slide.title}-${index}`}
                onClick={() => setActiveIndex(index)}
                aria-label={`Inspect slide ${index + 1}: ${slide.title}`}
                aria-pressed={safeActiveIndex === index}
                className="flex shrink-0 flex-col rounded-md p-3 text-left focus-ring"
                style={{
                  width: '9rem',
                  minHeight: '8rem',
                  background: slideBackground(index),
                  color: '#f8fafc',
                  border:
                    safeActiveIndex === index
                      ? '2px solid var(--brand)'
                      : '1px solid rgba(148, 163, 184, 0.2)',
                }}
              >
                <span className="text-[0.62rem] font-bold uppercase" style={{ color: '#f59e0b', letterSpacing: '0.1em' }}>
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="mt-2 text-xs font-semibold leading-snug" style={{ overflowWrap: 'anywhere' }}>
                  {shortText(slide.title, 46)}
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div
          className="grid gap-2 p-3"
          style={{
            gridTemplateColumns:
              slides.length === 1 ? 'minmax(0, 1fr)' : 'repeat(auto-fit, minmax(9rem, 1fr))',
          }}
        >
          {slides.map((slide, index) => (
            <section
              key={`${slide.title}-${index}`}
              aria-label={`${label} slide ${index + 1}`}
              className="flex flex-col rounded-md p-3"
              style={{
                background: slideBackground(index),
                color: '#f8fafc',
                aspectRatio: slides.length > 1 ? '1 / 1' : '4 / 5',
                justifyContent: slides.length > 1 ? 'flex-start' : 'space-between',
                minHeight: slides.length > 1 ? '10rem' : '12rem',
              }}
            >
              <div>
                <p className="text-[0.62rem] font-bold uppercase" style={{ color: '#f59e0b', letterSpacing: '0.14em' }}>
                  {String(index + 1).padStart(2, '0')} {slide.kicker}
                </p>
                <h4 className="mt-3 text-base font-bold leading-tight" style={{ overflowWrap: 'anywhere', letterSpacing: 0 }}>
                  {slide.title}
                </h4>
              </div>
              {slide.body && (
                <p
                  className="mt-4 whitespace-pre-line text-xs leading-relaxed"
                  style={{
                    color: '#cbd5e1',
                    maxHeight: slides.length > 1 ? '5rem' : index === 0 ? '8rem' : '7rem',
                    overflow: 'hidden',
                    overflowWrap: 'anywhere',
                  }}
                >
                  {shortText(slide.body, 150)}
                </p>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
