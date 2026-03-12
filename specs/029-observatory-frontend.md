# Spec 029: Observatory Frontend

**Status:** planned
**Phase:** Phase 2
**Author:** Juan
**Created:** 2026-03-12
**Updated:** 2026-03-12

## Problem

The Holus system runs autonomously — agents fire, content gets evaluated, costs accumulate, trajectories update — but there is no way to see any of it without tailing log files. Operators cannot answer basic questions like "which agent failed last night?" or "what did the system spend this week?" without digging through JSONL files manually. Prospective employers and interviewers cannot see the system working at all.

The Observatory API (spec 028) exposes all this data via REST + SSE. What is missing is the frontend that consumes it.

## Goals

- A dashboard loads in < 2s and shows real system health without any manual data wrangling
- Any agent's last 30 cycle results are visible in 3 clicks from the home page
- The content pipeline state (DRAFT / REVIEW / PUBLISHED) is visible at a glance
- Eval score trends are visible per-agent over the last 30 days
- Real-time trajectory events appear within 1s of the SSE push
- `just dev-observatory` starts both Observatory API and the frontend with a single command
- The UI works on mobile (responsive layout, no horizontal scroll on 375px viewport)
- Suitable as a live demo for interviews — polished, not prototype-quality

## Non-Goals

- Authentication / login — the Observatory is internal tooling, not a public product
- Write operations — no editing agents, content, or config from the UI; it is read-only
- Mobile app (native iOS/Android) — responsive web is sufficient
- Embedding or replacing Langfuse's own UI — the frontend calls the Observatory API, which calls Langfuse internally; the Langfuse UI is never surfaced

## Solution

A Next.js 15 App Router application consuming the Observatory API (FastAPI, spec 028) via fetch and SSE. Component stack: shadcn/ui as the base, Tremor for charts and KPI cards, Tailwind CSS for layout and theming. Dark mode via Tailwind's `dark:` class strategy.

The research findings (`.pipeline-state/research-observatory.md`) evaluated SvelteKit as a tighter FastAPI/SSE pairing, but Next.js 15 is chosen here because:
1. The rest of the portfolio (job-tracker, pilaster, genpeli) already uses React — interviewers can ask about the same stack across projects
2. shadcn/ui + Tremor is the documented 2026 consensus for this exact use case: React dashboard, KPI cards, sparklines, area charts
3. Next.js App Router supports React Server Components for the data-heavy static sections, while Client Components handle SSE

Data flow:

```
Observatory API (FastAPI, :8001)
  ├── GET /health          → Dashboard health banner
  ├── GET /agents          → Agent status grid
  ├── GET /agents/{id}     → Agent detail card + cycle history
  ├── GET /evaluations     → Eval heatmap data
  ├── GET /content         → Kanban board content
  ├── GET /knowledge       → File browser + MEMORY.md timeline
  ├── GET /costs           → Cost breakdown
  └── GET /trajectory/stream (SSE) → Real-time event list

Frontend (:3000)
  ├── Server Components fetch non-streaming endpoints (SWR via cache headers)
  └── Client Components subscribe to SSE for trajectory
```

The frontend lives in `observatory/frontend/` alongside the Observatory API at `observatory/api/`.

## Implementation Notes

### Directory Layout

```
observatory/
  api/           ← Observatory API (spec 028, FastAPI)
  frontend/
    app/
      page.tsx              ← Dashboard overview (/)
      agents/
        page.tsx            ← Agent grid redirect (unused, goes to /)
        [id]/
          page.tsx          ← Agent detail (/agents/[id])
      content/
        page.tsx            ← Content pipeline (/content)
      evaluations/
        page.tsx            ← Eval heatmap (/evaluations)
      knowledge/
        page.tsx            ← Knowledge browser (/knowledge)
      health/
        page.tsx            ← System health (/health)
      layout.tsx            ← Root layout (nav + dark mode)
    components/
      AgentCard.tsx
      AgentGrid.tsx
      KPICard.tsx
      TrajectoryTimeline.tsx
      QualityHeatmap.tsx
      ContentKanban.tsx
      FreshnessIndicator.tsx
      SystemHealthGrid.tsx
      CostPieChart.tsx
      KillSwitchBanner.tsx
    lib/
      api.ts                ← Typed fetch wrappers for Observatory API
      sse.ts                ← EventSource hook with cleanup
      types.ts              ← Shared response types (mirrors API schema)
    package.json
    tailwind.config.ts
    next.config.ts
```

### Pages

**Dashboard Overview (`/`)**
- System health banner at top (green / yellow / red based on `GET /health`)
- Four KPI cards (Tremor): total cycles this week, success rate, avg quality score, total cost
- Agent status grid: all agents color-coded by status (idle / running / error / disabled)
- Trajectory sparkline: last 7 days cycle count per day (Tremor AreaChart)
- Cost breakdown pie chart (Tremor DonutChart, per-agent)

**Agent Detail (`/agents/[id]`)**
- Agent info card: role, model, status, version from AGENTS.yaml (via API)
- Performance chart: quality scores over last 30 runs (Tremor LineChart)
- Cycle history table: last 30 runs — timestamp, status, quality score, cost, duration
- Capability breakdown: which rubric dimensions score highest / lowest (horizontal bar chart)

**Content Pipeline (`/content`)**
- Kanban board (read-only): DRAFT / REVIEW / PUBLISHED columns, cards show title + platform + pillar
- Calendar view: next 14 days, color-coded by pillar
- Platform distribution donut chart
- Pillar balance indicator (bar chart: authority / entertainment / education / conversion)

**Evaluations (`/evaluations`)**
- Quality score heatmap: agents (rows) × days (columns), color by score 0–10
- Evaluation history table: filterable by agent, date range, pass/review/fail
- Per-evaluator score distributions (violin plot or box-plot approximation via Tremor)
- Gate health summary: pass / review / fail counts for the last 30 days

**Knowledge (`/knowledge`)**
- File browser: lists `.self-improvement/memory/` + `docs/decisions/` files, sorted by modified date
- Freshness indicator per file: green < 7d, yellow 7–30d, red > 30d
- MEMORY.md timeline: markdown rendered inline
- Lessons learned: last 20 entries from `lessons.json`, newest first

**System Health (`/health`)**
- Service status grid: Observatory API, silos (genpeli-mcp, social-media-mcp, pilaster-mcp), Langfuse
- Kill switch state: large prominent banner — ACTIVE (red) or INACTIVE (green)
- Error rate chart: last 24h (Tremor AreaChart)
- Silo availability history: uptime % per silo over last 7 days

### Component Details

**`TrajectoryTimeline`**
- Client Component, uses `lib/sse.ts` hook
- Subscribes to `GET /trajectory/stream` on mount
- Cleans up EventSource on unmount to prevent memory leaks
- Keeps last 100 events in state (prevents unbounded array growth)
- Each event: timestamp, agent name, event type, short description

**`QualityHeatmap`**
- Renders a CSS grid: agents × last 30 days
- Color scale: red (0–4) → yellow (4–7) → green (7–10)
- Tooltip on hover: exact score, agent, date
- Falls back to "No data" cell when eval missing for that agent/day

**`FreshnessIndicator`**
- Colored dot (red / yellow / green) with tooltip showing last-modified timestamp
- Thresholds: green < 7 days, yellow 7–30 days, red > 30 days
- Used in Knowledge file browser

**`KillSwitchBanner`**
- Full-width banner at top of `/health` page
- If kill switch ACTIVE: red background, large text, timestamp of activation
- If INACTIVE: green background, subtle — system is running normally

### SSE Hook (`lib/sse.ts`)

```typescript
// useSseEvents(url: string): TrajectoryEvent[]
// - Creates EventSource on mount
// - Appends events to state, capped at maxEvents (default 100)
// - Calls source.close() on unmount
// - Returns events array (newest first)
```

### API Client (`lib/api.ts`)

All fetch calls go to `NEXT_PUBLIC_OBSERVATORY_URL` (env var, default `http://localhost:8001`). Functions return typed responses matching the Observatory API schema. Uses Next.js `fetch` with `{ next: { revalidate: 30 } }` for server-side caching (30s TTL for agent/eval data, no cache for health).

### Justfile Integration

```makefile
dev-observatory:
    cd observatory && \
    uvx run python -m api.main &
    cd observatory/frontend && pnpm dev
```

Runs both API (port 8001) and frontend (port 3000) concurrently for local development.

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| SSE max events | 100 | Prevents unbounded array growth in long-running sessions |
| API revalidate TTL | 30s | Fresh enough for monitoring, not hammering the API |
| Trajectory sparkline window | 7 days | Matches the agent's weekly review cadence |
| Cycle history limit | 30 | One month of daily agent runs; keeps table scannable |
| Freshness thresholds | 7d / 30d | Green = recent activity, yellow = aging, red = stale |

### Dependencies

- Depends on: Spec 028 (Observatory API — provides all data endpoints)
- Depended on by: nothing yet (standalone frontend)

## Alternatives Considered

### Alternative A: SvelteKit

The research findings recommend SvelteKit + FastAPI as the tightest SSE integration, with 50% smaller bundle. Rejected because the portfolio is React-first — Next.js 15 keeps the stack consistent across all projects, which matters for interview conversations. The SSE difference is marginal for an internal tool.

### Alternative B: Raw Recharts (no Tremor)

Tremor is built on Recharts and adds ~150KB gzipped. Using Recharts directly would be lighter. Rejected because Tremor's pre-built KPI cards, sparklines, and DonutChart components save 2–3 days of work for a dashboard that is not a product — build time matters more than bundle size here.

### Alternative C: Embed Langfuse UI

Langfuse has its own dashboard for traces, costs, and evals. Rejected because it is not customizable to Holus's agent taxonomy, it requires a separate auth session, and it cannot show the content pipeline or knowledge freshness views. The Observatory API wraps Langfuse as a data source; this frontend is the opinionated display layer.

## Edge Cases & Failure Modes

- **Observatory API is down:** All server-fetched pages show a "Service unavailable" banner. SSE hook retries with exponential backoff (max 30s interval). No crash.
- **Agent not found (`/agents/[id]`):** Next.js `notFound()` renders the 404 page. The API returns 404; the frontend propagates it.
- **SSE connection drops:** Browser reconnects automatically (EventSource spec). If backend is down, retry interval capped at 30s to avoid hammering.
- **Empty eval data (new agent, no runs):** Heatmap renders empty cells (grey), not blank space. KPI cards show "—" for missing metrics.
- **Kill switch is ACTIVE:** Health page shows red full-width banner. Dashboard header shows a smaller red pill "KILL SWITCH ON" on all pages.
- **Content pipeline is empty:** Kanban columns render empty column placeholders, not a broken layout.
- **Cost data missing (Langfuse tags not set):** Cost breakdown shows "Cost data unavailable" instead of a broken chart.

## Observability

This is a read-only frontend — no server-side state, no mutations, no background jobs. Observability requirements are minimal:

- Browser console logs SSE connection state (connected / disconnected / retrying)
- Next.js built-in error boundaries catch render failures; errors logged to console
- `NEXT_PUBLIC_OBSERVATORY_URL` visible in network tab for debugging fetch targets

## Rollback Plan

Frontend is a separate directory (`observatory/frontend/`) with no shared code with the Holus agent system. Rolling back means reverting the commits that added `observatory/frontend/`. The Observatory API (spec 028) is unaffected. No data migrations involved.

## Open Questions

- [ ] Does spec 028 (Observatory API) expose a `/costs` endpoint with per-agent cost breakdown, or does cost data need to be aggregated in the frontend from evaluation records? — @juan to check when implementing 028
- [ ] Is `just dev-observatory` the right Justfile target name, or does the project use a different convention? — @juan to confirm when wiring up

## Acceptance Criteria

- [ ] `pnpm dev` inside `observatory/frontend/` starts the dashboard on localhost:3000 without errors
- [ ] Dashboard (`/`) loads real data from Observatory API — KPI cards are not hardcoded
- [ ] Agent status grid shows all registered agents from `agents/AGENTS.yaml` (via API)
- [ ] `/agents/[id]` renders per-agent performance chart and cycle history table
- [ ] TrajectoryTimeline connects via SSE and displays new events within 1s of push
- [ ] `/evaluations` heatmap renders without error when eval data is present
- [ ] `/knowledge` file browser shows freshness indicators (green/yellow/red) correctly
- [ ] `/health` page shows kill switch state prominently (red banner if ACTIVE)
- [ ] All six pages are responsive at 375px viewport width (no horizontal scroll)
- [ ] Dark mode works via Tailwind `dark:` classes (system preference respected)
- [ ] `just dev-observatory` starts both API (port 8001) and frontend (port 3000)
- [ ] When Observatory API is unreachable, pages show an error banner rather than crashing
- [ ] `pnpm build` inside `observatory/frontend/` completes without TypeScript errors or lint failures
