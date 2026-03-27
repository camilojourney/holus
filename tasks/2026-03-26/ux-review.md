# UX Review -- Holus Observatory Frontend

**Date:** 2026-03-26
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** All pages and components in `observatory/frontend/src/`
**Method:** Source code review (no dev server running, no Playwright screenshots, no axe-core)

---

## Executive Summary

The Observatory is a well-structured Next.js dashboard with good foundations: responsive layout, dark mode, skip-to-content link, proper ARIA labels, and graceful error handling. The main UX gaps are in information hierarchy (everything has equal visual weight), missing interactive affordances (no sorting, no filtering on most pages), and a few accessibility issues that would fail WCAG 2.1 AA audits.

---

## Accessibility

### P0 -- Must Fix

**A1. Color contrast on muted text.** Multiple components use `text-gray-400 dark:text-gray-600` for secondary content. In dark mode, `gray-600` on `gray-950` has a contrast ratio of approximately 2.8:1, which fails WCAG 2.1 AA minimum of 4.5:1 for normal text. Affects: KPICard subtitles, TrajectoryTimeline timestamps, FreshnessIndicator labels, table metadata cells, Knowledge page file paths.
- **Files:** `KPICard.tsx:24`, `TrajectoryTimeline.tsx:34`, `FreshnessIndicator.tsx:14`, `TopPostRow.tsx:38`, `KnowledgePage.tsx:155`
- **Fix:** Use `text-gray-500 dark:text-gray-400` (contrast ratio ~5.5:1) for all secondary text.

**A2. Heatmap cells have no keyboard navigation.** `QualityHeatmap.tsx` renders a `role="grid"` with `role="gridcell"` elements, but cells are `<div>` elements with no `tabIndex`, no `onKeyDown`, and no focus styles. Screen readers will announce the grid but keyboard users cannot navigate it.
- **File:** `QualityHeatmap.tsx:69-74`
- **Fix:** Add `tabIndex={0}` to cells, implement arrow key navigation within the grid, add `focus-visible:ring-2` styles.

**A3. ContentDetailPanel trap focus.** The detail panel is a `role="dialog" aria-modal="true"` overlay, but there is no focus trap implementation. Tab key will cycle through elements behind the overlay. The close button uses a `x` character instead of an accessible icon.
- **File:** `ContentDetailPanel.tsx:109-116`
- **Fix:** Implement focus trap (use `@headlessui/react` Dialog which is already installed). Replace `x` close button with Lucide `X` icon and ensure it receives focus on panel open.

### P1 -- Should Fix

**A4. Missing `<thead>` scope attributes.** Tables in agent detail, evaluations, and engagement pages use `<th>` without `scope="col"`. Screen readers may not correctly associate header cells with data cells.
- **Files:** `agents/[id]/page.tsx:169`, `evaluations/page.tsx:84`, `engagement/page.tsx:214`
- **Fix:** Add `scope="col"` to all `<th>` elements.

**A5. Radio button groups need proper ARIA.** Engagement and Followers pages use `role="radiogroup"` with `role="radio"` buttons, but do not implement `aria-activedescendant` or arrow key navigation. The visual design implies radio behavior but the keyboard interaction model is click-only.
- **Files:** `engagement/page.tsx:137`, `followers/page.tsx:135`
- **Fix:** Add `onKeyDown` handler for arrow key navigation between radio options.

**A6. SVG charts lack text alternatives.** `GrowthChart.tsx`, `MiniChart` in `engagement/page.tsx`, and `GrowthLine` in `followers/page.tsx` have `aria-label` on the `<svg>` but no fallback for screen readers that cannot process SVG. No `<title>` element inside the SVG.
- **Files:** `GrowthChart.tsx:47`, `engagement/page.tsx:53`, `followers/page.tsx:52`
- **Fix:** Add `<title>` and `<desc>` elements inside each SVG.

### P2 -- Nice to Have

**A7. Motion preferences not respected.** The pulse animation on the trajectory live indicator and loading skeleton uses `animate-pulse` without checking `prefers-reduced-motion`. Some users may find continuous animation distracting.
- **Fix:** Add `motion-reduce:animate-none` to animated elements.

**A8. Language attribute.** `layout.tsx` sets `lang="en"` which is correct. But the About page references bilingual content (Spanish/English) without `lang="es"` spans for Spanish text fragments.

---

## Information Hierarchy

### P0 -- Must Fix

**H1. Dashboard KPI cards have no visual weight differentiation.** All four KPI cards (cycles, success rate, quality score, cost) have identical visual weight. The most important metric (quality score or success rate, depending on context) should be visually dominant. Currently all four are equal-sized boxes with the same typography.
- **File:** `page.tsx:62-100`
- **Fix:** Make the primary KPI card (e.g., success rate) larger or use a distinct background treatment. Consider a 2:1:1 or 1:1:1:1-with-highlight grid.

**H2. Agent grid has no grouping or filtering.** The agents page shows all agents in a flat grid. With 15+ agents (32 planned), this becomes unwieldy. There is a status summary bar at the top but no way to filter by status, type, or model tier.
- **File:** `agents/page.tsx:40-62`
- **Fix:** Add filter tabs (by type: manager/specialist/evaluator/ops) or group agents by type with section headers.

### P1 -- Should Fix

**H3. Sidebar navigation has 10 items with no grouping.** About, Dashboard, Agents, Content, Engagement, Followers, Evaluations, Knowledge, Health, Results. These could be grouped: "Overview" (About, Dashboard), "Content" (Content, Engagement, Followers, Results), "System" (Agents, Evaluations, Knowledge, Health).
- **File:** `Sidebar.tsx:23-34`
- **Fix:** Add section labels (small uppercase headers) between nav groups.

**H4. Evaluation history table shows raw records without summary statistics.** The evaluations page shows pass/review/fail counts at top and a heatmap, but the table below is a raw list with no aggregation. For 50+ records, this is a data dump.
- **File:** `evaluations/page.tsx:73-126`
- **Fix:** Add sparkline or trend indicator per agent in the table, or collapse by agent with expandable detail.

**H5. Knowledge page mixes three different content types.** Freshness summary, System Memory (MEMORY.md), Recent Lessons, and File Browser are all stacked vertically with equal visual weight. The System Memory is the most important but appears in the middle.
- **File:** `knowledge/page.tsx:44-173`
- **Fix:** Put System Memory in a prominent card at top. Move freshness summary to a sidebar or compact bar.

### P2 -- Nice to Have

**H6. No breadcrumbs.** Agent detail page (`/agents/[id]`) has no breadcrumb back to `/agents`. The browser back button works but there is no visual navigation path.

**H7. Results page vs. Engagement page vs. Followers page overlap.** Three pages show engagement metrics with different views. Results shows aggregated KPIs + top posts + pillar breakdown. Engagement shows daily engagement by platform. Followers shows follower growth. The relationship between these is not clear from the navigation.

---

## CTA Clarity

### P0 -- Must Fix

**C1. Content Kanban cards have no visible action affordance.** Cards in the Kanban are `<button>` elements that open the detail panel on click, but there is no visual indicator that they are clickable (no "view" icon, no underline, no "click to review" hint). Only the cursor changes on hover.
- **File:** `ContentKanban.tsx:105-137`
- **Fix:** Add a subtle "View" link or chevron icon on each card, or add a hover state that clearly indicates interactivity.

**C2. Detail panel "Approve & Post Now" is the most destructive action but has the most prominent styling.** The approve button is full-width indigo with the most visual weight. Reject is secondary (border-only). This is reversed from UX convention -- the destructive or irreversible action (approve = post to social media) should require more deliberation.
- **File:** `ContentDetailPanel.tsx:337-349`
- **Fix:** Swap visual weight. Make "Approve & Post Now" a secondary button. Add a confirmation step before posting. Or rename to "Approve" and separate "Post Now" as a distinct action.

### P1 -- Should Fix

**C3. No empty state CTAs.** When agents list is empty, the message is "No agents found. Ensure Observatory API is running..." This is a developer-oriented message. For a portfolio demo with demo mode, the empty state should never appear, but if it does, it should link to the About page.
- **Files:** `agents/page.tsx:34-37`, `evaluations/page.tsx:128-131`, `knowledge/page.tsx:134-136`

**C4. About page CTAs compete.** "View Dashboard" (primary) and "Engagement Tracker" (secondary) are placed side by side. The secondary CTA is oddly specific -- why Engagement Tracker specifically? Should be "Explore the System" or link to Agents.
- **File:** `about/page.tsx:87-99`

### P2 -- Nice to Have

**C5. Theme toggle has no label.** The sun/moon icon toggle at the bottom of the sidebar has `aria-label` but no visible text. New users may not understand what it does. Consider adding a tooltip.

---

## Design System Compliance

### P0 -- Must Fix

**D1. Tremor and Recharts are installed but unused.** `package.json` lists `@tremor/react@3.18.7` and `recharts@3.8.0` as dependencies. Zero imports of either library exist in any component. All charts are hand-rolled SVGs. This adds ~150KB+ to the bundle with no benefit.
- **Fix:** Either use them (recommended: replace GrowthChart, MiniChart, engagement sparklines with Tremor AreaChart) or remove them from dependencies.

**D2. `@headlessui/react` is installed but unused.** It's in the pnpm lockfile but not imported. The ContentDetailPanel dialog should use Headless UI's Dialog component for proper focus trapping and accessibility.
- **Fix:** Use `@headlessui/react` Dialog for ContentDetailPanel.

### P1 -- Should Fix

**D3. Inconsistent border radius.** Most cards use `rounded-xl` (12px). Status badges use `rounded-full`. Some internal elements use `rounded-lg` (8px) or `rounded` (4px) or `rounded-sm` (2px). The brand config defines `border_radius: 16` (px). No component references this value.
- **Fix:** Define a border radius token in CSS and use it consistently.

**D4. Color system duplication.** Status colors, platform colors, pillar colors, and verdict colors are defined as inline objects in 8+ components with slight variations. There is no shared color token file.
- **Files:** `AgentCard.tsx:4-11`, `ContentKanban.tsx:19-37`, `ContentDetailPanel.tsx:22-35`, `PlatformCard.tsx:3-9`, `TopPostRow.tsx:3-8`, `evaluations/page.tsx:8-12`, `engagement/page.tsx:9-31`, `followers/page.tsx:9-22`
- **Fix:** Create `lib/colors.ts` exporting shared color token maps.

**D5. `fmt()` helper duplicated 4 times.** The number formatting function (`1000` -> `1K`, `1000000` -> `1M`) is copy-pasted in `PlatformCard.tsx`, `PillarBreakdown.tsx`, `TopPostRow.tsx`, `engagement/page.tsx`, `followers/page.tsx`, and `results/page.tsx`.
- **Fix:** Move to `lib/format.ts` and import.

### P2 -- Nice to Have

**D6. No component documentation or Storybook.** 15 components with no visual documentation. For a portfolio piece, a Storybook instance showing components in isolation would strengthen the "frontend engineering" signal.

**D7. No error boundary.** The spec (029) mentions "Next.js built-in error boundaries catch render failures" but no `error.tsx` files exist at any route level.

---

## Responsive Design

### P1 -- Should Fix

**R1. Heatmap overflows on mobile.** `QualityHeatmap.tsx` uses `overflow-x-auto` on the container but the 30-column grid with `w-7` cells (7*30 = 210px + 128px label = 338px minimum) will cause horizontal scroll on small screens. The spec requires "no horizontal scroll on 375px viewport."
- **Fix:** On mobile, show last 7 days instead of 30, or switch to a vertical list view.

**R2. Engagement table not readable on mobile.** The platform breakdown table has 7 columns (Platform, Impressions, Likes, Comments, Shares, Posts, Eng. Rate). On 375px viewport this will definitely scroll horizontally.
- **Fix:** On mobile, switch to a card-based layout per platform, or hide low-priority columns.

**R3. Content Kanban forces 4-column layout on lg.** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` means on tablets (768-1023px) the board shows only 2 columns of 4 statuses, requiring vertical scroll to see all. On mobile, each column stacks vertically -- the "board" metaphor breaks down entirely.
- **Fix:** On mobile, switch to a tabbed interface (one tab per status) or a flat list grouped by status.

### P2 -- Nice to Have

**R4. Sidebar width is fixed at `w-56` (224px).** On a 1024px screen, this leaves 800px for content. On a 768px screen, the sidebar is hidden (mobile mode kicks in). There is no collapsible sidebar state for medium screens.

---

## Performance Concerns

### P1 -- Should Fix

**P1. Demo data generates random data on every render.** `generateEngagementData()` and `generateFollowerData()` in `demo-data.ts` call `Math.random()` inside `useMemo(() => ..., [])`. On the server side, this generates different data per request, causing hydration mismatches in production. The engagement and followers pages are client components (`'use client'`) which avoids SSR hydration issues, but the data will still differ between page loads, which is confusing for a demo.
- **Fix:** Use a seeded random number generator so demo data is deterministic.

**P2. SSE hook creates EventSource on mount even in demo mode.** `useTrajectoryStream()` always attempts to connect to the API SSE endpoint, even when `NEXT_PUBLIC_DEMO_MODE=true`. This generates console errors on every page load in demo mode.
- **Fix:** Check demo mode before creating EventSource. Return static demo events instead.

---

## Fix Plan Summary

| Priority | Count | Examples |
|----------|:-----:|---------|
| **P0** | 6 | Color contrast (A1), heatmap keyboard nav (A2), focus trap (A3), KPI hierarchy (H1), Kanban affordance (C1), approve button weight (C2) |
| **P1** | 11 | Table scopes (A4), radio key nav (A5), SVG alts (A6), agent filtering (H2), sidebar grouping (H3), eval table summary (H4), knowledge hierarchy (H5), Tremor/Recharts usage (D1), Headless UI Dialog (D2), heatmap mobile (R1), demo data hydration (P1) |
| **P2** | 7 | Motion preferences (A7), breadcrumbs (H6), page overlap (H7), empty state CTAs (C3), about page CTA (C4), theme label (C5), border radius tokens (D3) |
| **P3** | 4 | Storybook (D6), error boundary (D7), collapsible sidebar (R4), SSE in demo mode (P2) |

**Total findings: 28**
