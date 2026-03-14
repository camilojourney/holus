# UX Fix Plan — holus — holus-UX-20260312-f7663e5f

## P0 (Critical — fix now)

- [ ] **Mobile sidebar collapse** | File: `src/components/Sidebar.tsx` | Actual: Fixed `w-56`, no hamburger | Fix: Add mobile slide-over with hamburger button, hide sidebar below `md` breakpoint, show overlay on toggle
- [ ] **Loading states for all routes** | File: `src/app/loading.tsx` (new) + per-route `loading.tsx` | Actual: No loading UI, pages pop in | Fix: Create `loading.tsx` with skeleton cards matching each page's layout (KPI skeletons, agent grid skeletons, etc.)

## P1 (High — fix now)

- [ ] **Replace Unicode nav icons with Lucide** | File: `src/components/Sidebar.tsx:7-12` | Actual: `▦ ◈ ◰ ◎ ◻ ◉` | Fix: Install `lucide-react`, use `LayoutDashboard`, `Users`, `FileText`, `Target`, `BookOpen`, `Activity` icons
- [ ] **Add `aria-current="page"` to active nav** | File: `src/components/Sidebar.tsx:32` | Actual: Only visual highlight | Fix: Add `aria-current={active ? 'page' : undefined}` to Link
- [ ] **Add `role="alert"` to KillSwitchBanner** | File: `src/components/KillSwitchBanner.tsx` | Actual: No ARIA role | Fix: Add `role="alert" aria-live="assertive"` to banner div
- [ ] **Increase nav link touch targets** | File: `src/components/Sidebar.tsx:35` | Actual: `py-2` ≈ 36px | Fix: Change to `py-2.5` for ≈44px
- [ ] **Add dark mode toggle** | File: `src/components/Sidebar.tsx:47-49` | Actual: System preference only | Fix: Add sun/moon toggle button in sidebar footer that toggles `dark` class on `<html>`
- [ ] **Add `<nav aria-label>` wrapper** | File: `src/components/Sidebar.tsx:28` | Actual: `<nav>` without label | Fix: `<nav aria-label="Main navigation">`

## P2 (Medium — skip for now)

- [ ] **KPI sparklines** | File: `src/components/KPICard.tsx` | Spec calls for Tremor AreaChart micro-charts inside KPI cards. Requires `sparkline` data from API.
- [ ] **Cost DonutChart** | File: `src/app/page.tsx` | Spec calls for Tremor DonutChart with per-agent cost breakdown. Requires `/costs` or cost data from `/metrics`.
- [ ] **Trajectory sparkline** | File: `src/app/page.tsx` | Spec calls for 7-day Tremor AreaChart. Requires `sparkline` data from KPIMetrics.
- [ ] **Heatmap keyboard navigation** | File: `src/components/QualityHeatmap.tsx` | No `role="grid"`, no arrow key support.

## P3 (Low — skip for now)

- [ ] **Heatmap contrast in light mode** | `QualityHeatmap.tsx:11-13` | `bg-green-400` on white may be low contrast
- [ ] **Favicon and OG meta** | No favicon, no Open Graph tags for link previews
- [ ] **TrajectoryTimeline SSE status aria-label** | `TrajectoryTimeline.tsx:19-21` | Status dot has no screen reader text

## Summary
- P0: 2 | P1: 6 | P2: 4 | P3: 3
