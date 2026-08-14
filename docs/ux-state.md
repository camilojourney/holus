# UX State — Holus Observatory

**Last updated:** 2026-08-14
**Overall status:** PUBLIC DEMO + LOCAL DEVELOPMENT: the public surface uses clearly labelled demonstration state; live Observatory data and events require an authenticated backend connection.

---

## Current Surfaces

| Surface | State | Tech | Location |
|---------|-------|------|----------|
| Dashboard (`/`) | Functional | Next.js 16 RSC + Tremor | `observatory/frontend/src/app/page.tsx` |
| Generation Studio (`/studio`) | Functional demo | Local Holus adapter | `observatory/frontend/src/app/studio/page.tsx` |
| Agents grid (`/agents`) | Functional | Next.js RSC | `src/app/agents/page.tsx` |
| Agent detail (`/agents/[id]`) | Functional | Next.js RSC + Recharts | `src/app/agents/[id]/page.tsx` |
| Content pipeline (`/content`) | Functional | Next.js RSC | `src/app/content/page.tsx` |
| Evaluations (`/evaluations`) | Functional | Next.js RSC + CSS Grid | `src/app/evaluations/page.tsx` |
| Knowledge (`/knowledge`) | Functional | Next.js RSC | `src/app/knowledge/page.tsx` |
| Health (`/health`) | Functional | Next.js RSC | `src/app/health/page.tsx` |
| Observatory API | Local backend | FastAPI + SSE | `src/holus/api/` - public/demo access requires an authenticated backend connection |

---

## Component Inventory

| Component | State | Issues |
|-----------|-------|--------|
| `Sidebar` | Working | Lucide icons, mobile drawer navigation, theme control, public-demo connection state, and API entry point. |
| `KPICard` | Working | Custom implementation, not using Tremor's `Card` component. No sparkline or trend indicator. |
| `AgentCard` | Working | Shows agent status, model, role. Links to detail page. |
| `TrajectoryTimeline` | Connection-gated | Client component with EventSource only for local authenticated development. Public/demo surfaces show that a connection is required and never open localhost SSE. |
| `GenerationStudio` | Safe demo | Local bounded lifecycle (`queued`, `generating`, `ready`, `error`) with no live job, external request, or artifact URL. |
| `QualityHeatmap` | Working | CSS grid, 32 agents × 30 days. Color scale red/yellow/green. Tooltip on hover. |
| `ContentKanban` | Working | Three-column DRAFT/REVIEW/PUBLISHED. Pillar badges. |
| `FreshnessIndicator` | Working | Colored dot with tooltip. Green <7d, yellow 7-30d, red >30d. |
| `KillSwitchBanner` | Working | Full-width red/green banner. Compact mode for dashboard header. |
| `ErrorBanner` | Working | Generic error message display. |
| `SystemHealthGrid` | Working | Service status cards with color-coded states. |

---

## Known UX Issues

| Severity | Surface | Issue |
|----------|---------|-------|
| P0 | All pages | No loading states — server components show nothing while fetching, then pop in. No skeleton screens. |
| P1 | Dashboard | KPI cards are custom divs, not using Tremor's pre-built `Card`/`Metric` components. Missing trend arrows and sparklines. |
| P1 | Dashboard | No cost breakdown pie chart (spec calls for Tremor DonutChart). |
| P1 | Dashboard | No trajectory sparkline chart (spec calls for 7-day Tremor AreaChart). |
| P1 | Agent detail | Performance chart may not use Tremor's LineChart. Capability breakdown bar chart not confirmed. |
| P2 | Content | Calendar view (next 14 days) not confirmed implemented. Spec calls for it. |
| P2 | Content | Platform distribution donut chart and pillar balance bar chart not confirmed. |
| P2 | Evaluations | Per-evaluator score distributions (violin/box plot) not confirmed. |
| P2 | General | No favicon or Open Graph meta tags for when links are shared. |
| P3 | General | No empty state designs for "no data" scenarios beyond basic text fallbacks. |

---

## What's Working Well

- **Data flow is solid**: RSC fetches via `lib/api.ts` with typed responses and `Promise.allSettled` for graceful degradation.
- **Connection honesty is enforced**: TrajectoryTimeline only opens SSE for local authenticated development; public/demo mode explicitly states that live events require a backend connection.
- **Error handling**: Pages degrade gracefully when API is unreachable (ErrorBanner, null checks).
- **Theme control**: The sidebar provides a persisted light/dark theme control.
- **Layout structure**: Sidebar + main content area pattern is clean, with a mobile drawer below the `md` breakpoint.

---

## Pending UX Work (from spec 029 acceptance criteria)

- [ ] Responsive layout at 375px viewport (currently broken — sidebar blocks content)
- [ ] Skeleton loading states for all server-fetched pages
- [ ] Tremor KPI cards with sparklines replacing custom KPICard
- [ ] Cost breakdown DonutChart on dashboard
- [ ] Trajectory sparkline AreaChart (7-day) on dashboard
- [ ] Agent detail LineChart for quality scores over 30 runs
- [ ] Content calendar view (14-day)
- [ ] Dark mode toggle (not just system preference)
- [ ] `pnpm build` completes without TypeScript errors
- [ ] `just dev-observatory` starts both API and frontend
- [ ] Proper icon library replacing Unicode characters

---

## Last Audit

No formal UX audit has been run. No axe-core accessibility scan. No Lighthouse performance test. No screenshot baseline captured.
