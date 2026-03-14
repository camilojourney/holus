# Code Map — Holus Observatory UX Audit

## 1. Routes & Pages

| Route | File | Status |
|-------|------|--------|
| `/` | `src/app/page.tsx` | Functional — KPIs, agent grid, trajectory timeline |
| `/agents` | `src/app/agents/page.tsx` | Redirect/grid |
| `/agents/[id]` | `src/app/agents/[id]/page.tsx` | Agent detail with cycle history |
| `/content` | `src/app/content/page.tsx` | Kanban board |
| `/evaluations` | `src/app/evaluations/page.tsx` | Quality heatmap |
| `/knowledge` | `src/app/knowledge/page.tsx` | File browser |
| `/health` | `src/app/health/page.tsx` | System health + kill switch |

## 2. Button & Touch Target Audit

No interactive buttons exist (read-only dashboard). All clickable elements are:
- Sidebar nav links: `px-3 py-2` = ~36px height (below 44px minimum)
  - File: `src/components/Sidebar.tsx:35`
- AgentCard link: full card is clickable, adequate target size
  - File: `src/components/AgentCard.tsx:19`

## 3. Color & Theme Issues

No hardcoded hex colors found. All colors use Tailwind semantic classes with `dark:` variants. Good.

Minor: Heatmap uses `bg-green-400`/`bg-yellow-400`/`bg-red-400` which may have insufficient contrast against white background in light mode.
- File: `src/components/QualityHeatmap.tsx:11-13`

## 4. Accessibility Gaps

- **Sidebar nav**: No `aria-current="page"` on active link — `src/components/Sidebar.tsx:32`
- **Sidebar nav**: No `<nav aria-label="Main navigation">` — `src/components/Sidebar.tsx:28`
- **KillSwitchBanner**: No `role="alert"` for critical system state — `src/components/KillSwitchBanner.tsx`
- **QualityHeatmap**: No keyboard navigation, no `role="grid"` — `src/components/QualityHeatmap.tsx:42`
- **TrajectoryTimeline**: SSE status dot has no screen reader label — `src/components/TrajectoryTimeline.tsx:19-21`
- **AgentCard**: Status badge has no `aria-label` — `src/components/AgentCard.tsx:25`

## 5. Loading & Skeleton States

- All pages use RSC `async` functions with `Promise.allSettled` — good error handling
- **No skeleton/loading states**: Pages show nothing while server fetches data, then pop in all at once
  - `src/app/page.tsx:24` — no `loading.tsx` or Suspense boundary
  - `src/app/health/page.tsx:8` — no `loading.tsx`
  - Same for all other pages

## 6. Form UX Issues

No forms exist — dashboard is read-only. N/A.

## 7. Empty States

- KPICard: Shows "—" for missing data (adequate) — `src/app/page.tsx:66`
- Agent grid: Shows "No agents registered" text (adequate) — `src/app/page.tsx:108`
- QualityHeatmap: Shows "No agent data available" — `src/components/QualityHeatmap.tsx:36`
- ContentKanban: Shows "Empty" per column — `src/components/ContentKanban.tsx:49`
- SystemHealthGrid: Shows "No service data available" — `src/components/SystemHealthGrid.tsx:16`
- TrajectoryTimeline: Shows "Waiting for events..." — `src/components/TrajectoryTimeline.tsx:28`

All empty states are text-only. No illustrations or CTAs. Acceptable for internal tool.

## 8. Mobile/Responsive Issues

- **Sidebar**: Fixed `w-56` (224px), no collapsible behavior, no hamburger menu — `src/components/Sidebar.tsx:19`
- **Layout**: `flex min-h-screen` with no mobile breakpoint to stack — `src/app/layout.tsx:31`
- **Heatmap**: `overflow-x-auto` handles horizontal scroll well — `src/components/QualityHeatmap.tsx:43`
- **KPI grid**: `grid-cols-2 lg:grid-cols-4` — works on mobile (good) — `src/app/page.tsx:62`
- **Agent grid**: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` — works (good) — `src/app/page.tsx:111`
- **ContentKanban**: `grid-cols-1 sm:grid-cols-3` — works (good) — `src/components/ContentKanban.tsx:35`

Only the sidebar is truly broken on mobile.

## 9. Typography Scale

Consistent usage of Tailwind text scale:
- `text-2xl font-bold` — page headings
- `text-sm font-semibold` — section headings
- `text-xs` — metadata, labels, badges
- `font-mono` — timestamps in trajectory

No text below 11px. Adequate.

## 10. Top 10 P0/P1 Issues

### P0 (blocks interview demo quality)
1. **No mobile sidebar collapse** — Sidebar blocks all content on mobile. Need hamburger menu or slide-over. `Sidebar.tsx:19`
2. **No loading states** — All pages pop in after server fetch. Need `loading.tsx` files with skeleton screens for all 6 routes.

### P1 (significant quality gap from spec)
3. **KPICard missing sparklines** — Spec calls for Tremor AreaChart sparkline in KPI cards. Current is plain number. `KPICard.tsx:16`
4. **No cost DonutChart** — Spec 029 calls for cost breakdown pie chart on dashboard. Not implemented. `page.tsx`
5. **No trajectory sparkline** — Spec calls for 7-day Tremor AreaChart. Not implemented. `page.tsx`
6. **Unicode nav icons** — Sidebar uses `▦ ◈ ◰ ◎ ◻ ◉` instead of Lucide/Heroicons. Looks unprofessional. `Sidebar.tsx:7-12`
7. **No dark mode toggle** — Only system preference. Need manual toggle in sidebar footer. `Sidebar.tsx:47`
8. **No `aria-current` on active nav** — Screen reader can't identify current page. `Sidebar.tsx:32`
9. **No `role="alert"` on KillSwitchBanner** — Critical system state not announced. `KillSwitchBanner.tsx`
10. **Nav link touch targets too small** — `py-2` ≈ 36px, below 44px WCAG minimum. `Sidebar.tsx:35`
