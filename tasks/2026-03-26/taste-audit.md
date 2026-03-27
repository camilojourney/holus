# Taste Audit -- Holus Observatory Frontend

**Date:** 2026-03-26
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** All source files in `observatory/frontend/src/` + `config/brand-visual.yaml` + backend visual pipeline (`src/holus/visual/`)

---

## Overall Scores

| Dimension | Score (1-10) | Notes |
|-----------|:---:|-------|
| **Visual Craft** | 7 | Clean, consistent Tailwind. Missing visual polish that separates "well-built internal tool" from "portfolio showpiece." |
| **Content Quality** | 8 | Demo data is realistic, well-calibrated, and tells a coherent story. About page copy is strong. |
| **Brand Alignment** | 6 | Frontend uses generic gray/indigo Tailwind palette. Backend has a carefully designed brand system (`brand-visual.yaml`) that the frontend ignores entirely. |

---

## Visual Craft: 7/10

### What it looks like now

A competent Next.js dashboard built with Tailwind utility classes, Geist fonts, and Lucide icons. Dark mode by default. Cards, tables, and grids are well-proportioned. The sidebar is responsive with a slide-over mobile menu. Loading skeleton matches the actual layout. Every page follows the same spacing rhythm (`px-6 py-6 space-y-6`).

### What it should look like

A **portfolio-grade operations dashboard** that makes interviewers stop scrolling. The spec says "Suitable as a live demo for interviews -- polished, not prototype-quality" (spec 029). Right now it clears "not prototype" but does not reach "makes you want to ask about it."

### Specific observations

**Looks like:** A generic Tailwind admin template (gray-50/gray-900 card system, indigo accents).
**Should look like:** A branded observatory with the deep navy (`#0A0F1E`) and indigo (`#6366F1`) palette from `brand-visual.yaml`, Plus Jakarta Sans headings, JetBrains Mono for metrics/data.

**Looks like:** KPI cards are flat rectangles with text. No visual weight hierarchy.
**Should look like:** KPI cards with subtle gradients, micro-animations on value change, and visual differentiation between "this is the number" and "this is the label." The `@tremor/react` library is installed but never used for KPI cards -- Tremor's `Card` + `Metric` components exist for exactly this.

**Looks like:** Charts are hand-rolled SVG polylines/area fills. Functional but basic.
**Should look like:** Recharts or Tremor chart components with tooltips, responsive resizing, and gradient fills. The project installs `recharts@3.8.0` and `@tremor/react@3.18.7` but never imports them in any component.

**Looks like:** The quality heatmap is a CSS grid of colored squares. No hover interaction beyond `title` attributes.
**Should look like:** A proper heatmap with tooltip overlays showing score + agent + date. GitHub contribution graph style, not spreadsheet style.

**Looks like:** Tables (cycle history, evaluation history, engagement breakdown) are plain HTML tables with hover backgrounds.
**Should look like:** Tables with sticky headers, sortable columns, and row-hover card expansion. The data density is appropriate but the interaction layer is missing.

**Looks like:** The sidebar logo area says "HOLUS" in small caps + "Observatory" in bold. No logo, no icon, no visual identity.
**Should look like:** A logo mark or icon that anchors the brand. Even a simple SVG mark (a circle with radiating lines = "observatory") would elevate the brand signal from "internal tool" to "product."

**Looks like:** Status badges (active, idle, running, error) are plain rounded-full pills.
**Should look like:** Status badges with subtle pulse animation for "running" and "active," matching the live trajectory indicator which already does this well.

### What's genuinely good

- The **skip-to-content link** is properly implemented (sr-only with focus:not-sr-only)
- **Dark mode** is not an afterthought -- every component has correct dark: variants
- **Loading skeleton** matches the dashboard layout precisely
- **Spacing consistency** -- every page uses the same `px-6 py-6 space-y-6` rhythm
- **Responsive breakpoints** are thoughtful: 1-col mobile, 2-col tablet, 3-4 col desktop
- The **About page** is beautifully structured -- hero with live indicator, agent loop cards, product showcase, technical stack grid, and personal footer
- **ContentDetailPanel** slide-over is well-designed: sticky header/footer, A/B visual comparison, agent trace display

---

## Content Quality: 8/10

### What it looks like now

Demo data tells a believable story: 15 agents across 4 categories, realistic engagement numbers (1.8K LinkedIn followers, 6.2% engagement rate), content pieces with quality scores, trajectory events with specific decisions and rationale.

### What it should look like

The content is already strong. Minor improvements would push it to 9/10.

### Specific observations

**Strong:** Post titles are specific and compelling ("How I Built a 32-Agent AI Marketing System," "MCP vs Skills: Two Paradigms for Extending AI Agents"). These read like real LinkedIn posts, not test data.

**Strong:** Trajectory events contain strategic reasoning ("Tutorials outperform promo posts 4:1 based on last 30d data"). This shows the system is making data-driven decisions, which is exactly the portfolio signal to send.

**Strong:** Lessons are specific and actionable ("Posts with code snippets get 2.4x more engagement than text-only posts"). They demonstrate genuine self-improvement, not placeholder content.

**Weak:** System Memory content is static text in demo-data.ts. Should be rendered as Markdown with proper formatting (headings, bold, bullet points). Currently rendered as `<pre>` in the Knowledge page, which loses the Markdown formatting.

**Weak:** Agent model labels show "claude-opus-4-6" and "claude-sonnet-4-6" -- the raw model IDs. Should display human-readable names ("Claude Opus 4.6", "Claude Sonnet 4.6", "Gemini 2.5 Pro") for the recruiter audience.

**Weak:** About page says "Next.js 16 + Tailwind" but package.json shows `"next": "16.1.6"` -- accurate but the spec (029) says "Next.js 15 App Router." Minor version inconsistency in the spec vs. reality.

**Missing:** No favicon or Open Graph meta tags. When shared on LinkedIn or Slack, the link preview would show generic Next.js defaults. For a portfolio piece that will be shared with recruiters, this matters.

---

## Brand Alignment: 6/10

### What it looks like now

Two completely disconnected brand systems:
1. **Backend visual pipeline** (`config/brand-visual.yaml`): A fully designed brand identity with 5 color themes, 4 font pairings, spacing system, safe zones, contrast ratios, and CSS variable generation.
2. **Frontend Observatory**: Generic Tailwind gray/indigo palette with Geist fonts. No reference to the brand system whatsoever.

### What it should look like

The Observatory should consume `brand-visual.yaml` or at minimum reflect its color palette and typography choices. The brand system defines `primary: #6366F1` (indigo) which the frontend happens to use via Tailwind's `indigo-*` classes, but this is coincidental -- the frontend has no code that reads or references the brand config.

### Specific observations

**Looks like:** The frontend was built independently by someone who chose similar colors by accident.
**Should look like:** The frontend applies the brand system intentionally. CSS custom properties from `brand.to_css_variables()` should be injected into `globals.css` or `layout.tsx`.

**Looks like:** Body text uses Geist Sans (Vercel's font). Data uses Geist Mono.
**Should look like:** Headlines use Plus Jakarta Sans (800 weight). Body uses Plus Jakarta Sans (400). Code/metrics use JetBrains Mono. These are the brand-defined font pairings in the "tech" preset.

**Looks like:** Background is `bg-gray-50` (light) / `bg-gray-900` (dark). Card surface is `bg-white` / `bg-gray-950`.
**Should look like:** Background is `#0A0F1E` (deep navy). Card surface is `#0F172A` (slate-900). Accent text is `#A5B4FC` (indigo-300). These are the specific brand tokens.

**Looks like:** The warm, cool, and bold themes in `brand-visual.yaml` exist but have no consumer.
**Should look like:** The Observatory has a theme selector (or at minimum respects the default dark theme), using the exact hex values from the brand config.

### Brand signal for interviews

The backend brand system is impressive engineering -- multi-tenant themes, font pairing presets, safe zones, contrast ratio enforcement. But none of it is visible in the Observatory, which is the one piece interviewers will actually see. This is a missed opportunity. The brand.py loader with `to_css_variables()` already generates the CSS; it just needs to be wired into the frontend build.

---

## Summary: Top 5 Taste Improvements

1. **Wire the brand system into the frontend.** Replace Geist fonts with Plus Jakarta Sans / JetBrains Mono. Replace generic gray palette with `brand-visual.yaml` colors. This is the single highest-leverage change.

2. **Use the installed chart libraries.** Recharts and Tremor are in package.json but unused. Replace hand-rolled SVG charts with Tremor AreaChart/DonutChart. This gets tooltips, responsive resizing, and gradient fills for free.

3. **Add a logo mark to the sidebar.** Even a simple `<svg>` icon (telescope, eye, satellite dish) in the brand primary color. The sidebar currently says "HOLUS / Observatory" in plain text.

4. **Add micro-interactions.** Pulse animation on "running" agent badges (already done on the trajectory live indicator). Value transition animations on KPI cards. Subtle hover elevation on cards.

5. **Add Open Graph meta tags and a favicon.** When an interviewer shares the link, it should show "Holus Observatory -- 32-agent AI marketing system" with a branded preview image, not the Next.js default.
