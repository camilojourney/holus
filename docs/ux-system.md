# Design System — Holus Observatory

**Last updated:** 2026-08-14
**Status:** PUBLIC DEMO + LOCAL DEVELOPMENT: the product presents safe demonstration state publicly and requires an authenticated backend for live operational data.

---

## Brand Identity

The Observatory is Holus's public product experience and a recruiter-facing demonstration of its orchestration layer. It must make the safe demo boundary unmistakable: local demonstration state is labelled, while live operational data requires an authenticated backend. The aesthetic is: modern AI product surface - clear, spacious, and selectively information-dense. Think: Vercel Analytics, Linear, Grafana Cloud. Not: Notion or generic dashboard-card sprawl.

Dark mode is the primary mode — operators monitor dashboards in varied lighting, and dark backgrounds make colored status indicators (green/yellow/red) more visible.

---

## Color Palette

Tailwind CSS 4 color tokens. All colors used via Tailwind utility classes.

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| Background | `gray-50` | `gray-900` | Page background |
| Surface | `white` | `gray-950` | Cards, sidebar, panels |
| Surface raised | `gray-50` | `gray-800` | Hover states, elevated surfaces |
| Border | `gray-200` | `gray-800` | Dividers, card borders |
| Text primary | `gray-900` | `white` | Headings, primary content |
| Text secondary | `gray-500` | `gray-400` | Labels, metadata, descriptions |
| Text muted | `gray-400` | `gray-400` | Placeholder text, footer (gray-600 fails WCAG AA on dark bg) |
| Accent | `indigo-600` | `indigo-400` | Active nav, primary actions, links |
| Active bg | `indigo-50` | `indigo-950` | Active nav item background |

### Status Colors (semantic — used across all pages)

| Status | Light | Dark | When |
|--------|-------|------|------|
| Healthy / Pass / Green | `green-600` bg `green-50` | `green-400` bg `green-950` | System healthy, agent idle/success, eval pass, fresh <7d |
| Warning / Review / Yellow | `yellow-600` bg `yellow-50` | `yellow-400` bg `yellow-950` | System degraded, eval review, aging 7-30d |
| Error / Fail / Red | `red-600` bg `red-50` | `red-400` bg `red-950` | System unhealthy, agent error, eval fail, stale >30d, kill switch active |
| Info / Default / Blue | `blue-600` bg `blue-50` | `blue-400` bg `blue-950` | Running state, info messages, cycles count |

### Heatmap Color Scale (Evaluations page)

| Score Range | Color | Meaning |
|------------|-------|---------|
| 0 - 4 | Red | Failing quality |
| 4 - 7 | Yellow | Needs improvement |
| 7 - 10 | Green | Passing quality |
| No data | Gray (`gray-200`/`gray-800`) | No evaluation run |

---

## Typography

| Token | Value | Usage |
|-------|-------|-------|
| Sans font | `Plus Jakarta Sans` (via `next/font/google`) | All UI text |
| Mono font | `JetBrains Mono` (via `next/font/google`) | Request IDs, permitted job state, timestamps |
| Page heading | `text-2xl font-bold` (24px) | Page titles |
| Section heading | `text-sm font-semibold` (13px) | Section labels ("Agents (32)") |
| Body | `text-sm` (14px) | Card content, table cells |
| Label | `text-xs` (12px) | Metadata, timestamps, subtitles |
| Line height | Default Tailwind | Body and headings |

---

## Spacing

Tailwind default spacing scale (4px base).

| Context | Value | Usage |
|---------|-------|-------|
| Page padding | `px-6 py-6` | Main content area |
| Section gap | `space-y-6` | Between major sections |
| Card grid gap | `gap-4` | Between cards in a grid |
| Card padding | `px-4 py-3` | Inside cards and banners |
| Sidebar width | `w-56` (224px) | Fixed sidebar |
| Sidebar padding | `px-5 py-5` | Sidebar header and footer |
| Nav item padding | `px-3 py-2` | Sidebar navigation links |

---

## Component Library Stack

| Layer | Library | Version | Purpose |
|-------|---------|---------|---------|
| Base components | Tailwind CSS 4 | ^4 | Layout, spacing, colors, responsive |
| Chart components | Tremor | ^3.18.7 | KPI cards, area charts, donut charts, line charts |
| Low-level charts | Recharts | ^3.8.0 | Custom chart configurations (under Tremor) |
| Icons | Lucide React | ^0.577.0 | Navigation and status affordances |

### Component Mapping (spec 029 → library)

| Spec Component | Implementation | Library |
|----------------|---------------|---------|
| KPI cards (4) | `KPICard.tsx` (custom) | Should use Tremor `Card` + `Metric` |
| Trajectory sparkline | Not implemented | Tremor `AreaChart` |
| Cost breakdown | Not implemented | Tremor `DonutChart` |
| Agent performance chart | Partially implemented | Tremor `LineChart` |
| Quality heatmap | `QualityHeatmap.tsx` | Custom CSS Grid (appropriate) |
| Content kanban | `ContentKanban.tsx` | Custom Tailwind (appropriate) |
| Health status grid | `SystemHealthGrid.tsx` | Custom Tailwind (appropriate) |
| Kill switch banner | `KillSwitchBanner.tsx` | Custom Tailwind (appropriate) |

---

## Layout

```
┌──────────────────────────────────────────────────┐
│ Sidebar (224px)  │  Main Content (flex-1)         │
│                  │                                │
│ ┌──────────────┐ │  ┌────────────────────────┐   │
│ │ HOLUS        │ │  │ Page Heading           │   │
│ │ Observatory  │ │  │ Subtitle               │   │
│ ├──────────────┤ │  ├────────────────────────┤   │
│ │ ▦ Dashboard  │ │  │ Health Banner           │   │
│ │ ◈ Agents     │ │  ├────────────────────────┤   │
│ │ ◰ Content    │ │  │ KPI Cards (4-col grid) │   │
│ │ ◎ Evaluations│ │  ├────────────────────────┤   │
│ │ ◻ Knowledge  │ │  │ Agent Grid (4-col)     │   │
│ │ ◉ Health     │ │  ├────────────────────────┤   │
│ ├──────────────┤ │  │ Trajectory Timeline    │   │
│ │ Read-only    │ │  └────────────────────────┘   │
│ └──────────────┘ │                                │
└──────────────────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Layout Change |
|------------|---------------|
| `xl` (1280px+) | 4-column agent grid, full sidebar |
| `lg` (1024px+) | 4-column KPI, 3-column agent grid |
| `sm` (640px+) | 2-column KPI, 2-column agent grid |
| Mobile (<640px) | Sidebar collapses to hamburger menu, 1-column everything |

**Current state:** Mobile navigation uses a drawer below the `md` breakpoint; the desktop sidebar remains 224px wide.

---

## Interaction Patterns

| Pattern | Implementation |
|---------|---------------|
| Navigation | Sidebar links with active state highlight (indigo) |
| Data refresh | RSC with 30s `revalidate` — no manual refresh button |
| Real-time updates | SSE via EventSource hook for local authenticated development only; public/demo mode states that a connection is required |
| Error handling | `Promise.allSettled` + `ErrorBanner` on API failure |
| Empty states | Text fallback ("No agents registered", "Unable to load") |
| Click-through | Agent card → agent detail page |
| Tooltips | Heatmap cells show score on hover |

### What Should NOT Exist

- No live publishing, operator, or account-management controls on the public surface
- No browser authentication flow: authenticated connections belong behind the future Holus BFF
- No onboarding or tutorials — the user is the builder
- No notification toasts — status is shown inline via banners and colors
- No chat interface — Holus is not a chatbot

---

## Dark Mode

- Implementation: Tailwind `dark:` variant classes
- Trigger: Persisted sidebar toggle, defaulting to dark mode
- Manual toggle: Available in the sidebar footer
- Primary mode for development and demo

---

## Accessibility Notes (not yet audited)

- Color alone should not be the only indicator — combine with icons/text labels
- All interactive elements need visible focus rings
- Heatmap needs keyboard navigation and screen reader support
- Status banners should use appropriate ARIA roles (`role="alert"` for kill switch)
- Sidebar navigation should be keyboard-navigable
