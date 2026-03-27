# Cycle 1 Taste Report — Holus Observatory Frontend

**Date:** 2026-03-26
**Reviewer:** Claude Opus 4.6 (automated UX loop)

## Overall Scores (Pre-Fix)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Visual Craft | 6/10 | Clean baseline but generic. No brand identity beyond Geist font. |
| Brand Identity | 4/10 | "Holus Observatory" has no logo, no brand color system, no visual mark. Looks like a template. |
| Content Quality | 8/10 | Demo data is realistic and well-structured. About page is excellent. |
| Layout/Hierarchy | 7/10 | Consistent page structure, good use of sections. But every card looks identical. |
| Interaction Design | 6/10 | Kanban, filters, SSE work. But no hover previews, no animations, no delight. |
| Accessibility | 7/10 | Has skip link, aria labels, role attributes. Missing: color contrast issues, focus rings inconsistent, no reduced-motion. |
| Responsiveness | 7/10 | Mobile sidebar works. Tables need better overflow handling. 5-col KPI grid breaks on tablet. |
| Typography | 6/10 | Only two sizes used (text-xs, text-sm). No visual weight hierarchy. Headings all look the same. |
| Color System | 5/10 | Hard-coded Tailwind colors everywhere. No design tokens. Dark mode uses gray-950 everywhere monotonously. |
| Component Polish | 6/10 | Components work but feel flat. No micro-animations, no depth, no visual rhythm. |

**Composite Score: 6.2/10**

## "Looks Like X, Should Look Like Y"

| Component | Looks Like | Should Look Like |
|-----------|-----------|-----------------|
| Dashboard | Generic admin template | Grafana-meets-Linear mission control |
| Sidebar | Plain list of links | Branded nav with active indicators, section dividers |
| KPI Cards | Flat boxes with numbers | Cards with sparklines/trends, accent borders |
| Agent Cards | Basic info cards | Identity cards with avatar/icon, status pulse |
| Health Banner | Full-width colored div | Subtle pill indicator, not shouting |
| Tables | Basic HTML tables | Polished data tables with sticky headers, row hover |
| Charts | SVG polylines | Smooth curves, gradient fills, tooltips |
| About Page | Documentation page | Polished marketing/portfolio landing |

## P0 Issues (Must Fix)

1. **No design token system** — Colors hardcoded as `gray-800`, `indigo-600` everywhere. A theme change requires editing 30+ files. Need CSS custom properties for brand colors.
2. **Insufficient heading hierarchy** — h1 is `text-2xl` everywhere. Sub-section headers are `text-sm font-semibold`. No visual breathing room between sections.
3. **Dark mode contrast issues** — `text-gray-600 dark:text-gray-600` used in about page (same color both modes). `text-gray-400 dark:text-gray-600` has poor contrast.
4. **No focus indicators on several interactive elements** — ContentKanban buttons, theme toggle needs visible focus ring.
5. **Missing heading levels** — KPI cards have no heading element, just `<p>` for title. Screen readers can't navigate by heading.

## P1 Issues (Should Fix)

6. **No brand accent/identity** — No logo mark, no gradient, no distinctive color. Every section uses indigo-600. Need a brand color token that differentiates Holus.
7. **Monotonous card styling** — Every card is `border border-gray-200 rounded-xl bg-white`. No depth variation, no hierarchy signals.
8. **No loading transitions** — Page switches are abrupt. No enter animations.
9. **No visual status indicators** — Agent status should pulse. Health dots should animate. System should feel alive.
10. **Mobile navigation has no backdrop blur** — Sidebar overlay uses `bg-black/50`, should use backdrop-blur for modern feel.
11. **Engagement page charts too small** — MiniChart is only 48px tall. Not useful for reading trends.
12. **Heatmap not responsive** — QualityHeatmap overflows on mobile with fixed `w-7` cells.
13. **Table headers not sticky** — Long tables require scrolling back to top to see column names.

## P2 Issues (Nice to Have)

14. Empty states are bare text. Should have illustrations or icons.
15. No page title animation/transition.
16. About page hero could use a subtle gradient background.
17. Content detail panel close button uses raw "x" character instead of lucide icon.
18. No tooltip component — everything uses `title` attribute.

## P3 Issues (Future)

19. Dark mode toggle doesn't persist to localStorage.
20. No keyboard shortcuts for navigation.
21. Charts should support touch interactions on mobile.
