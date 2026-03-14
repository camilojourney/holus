# UX Code Map — Holus Observatory

## 1. Routes & Pages
- `/` — Dashboard (KPI cards, agent grid, trajectory timeline)
- `/about` — Recruiter landing (hero, agent loop, products, tech stack)
- `/agents` — Agent list with status badges
- `/agents/[id]` — Agent detail (scores sparkline, cycle history table)
- `/content` — Content kanban (DRAFT/REVIEW/PUBLISHED)
- `/engagement` — Engagement tracker (filters, charts, tables)
- `/followers` — Follower tracker (growth chart, daily bars, tables)
- `/evaluations` — Quality heatmap + eval history
- `/health` — Service status grid + kill switch
- `/knowledge` — File browser with freshness indicators
- `/results` — Growth metrics, platform cards, top posts

## 2. Button & Touch Target Audit
- P0: QualityHeatmap.tsx — cells are `w-5 h-5` (20x20px), need 44x44px minimum
- P1: Sidebar theme toggle — `p-1.5` (~32px), borderline
- P1: Agent detail status badges — `text-xs px-1.5 py-0.5` (~24px height)
- P1: About page social icon buttons — `p-2` (40px), acceptable but tight

## 3. Color & Theme Issues
- P0: engagement/page.tsx — platformColors hardcoded hex (#2563eb, #ec4899, etc.)
- P0: followers/page.tsx — same platformColors + inline backgroundColor (#22c55e, #ef4444)
- P1: GrowthChart.tsx — SVG stopColor/stroke `rgb(99 102 241)` hardcoded
- P1: PillarBreakdown.tsx — pillarColors/productColors hardcoded Tailwind classes (acceptable but rigid)
- P1: PlatformCard.tsx — platform text colors hardcoded
- P1: TopPostRow.tsx — `text-[10px]` custom sizing bypasses design system

## 4. Accessibility Gaps
- P0: About page social links (Globe, LinkedIn, GitHub) — missing aria-label
- P0: About page pulsing dot — no aria-label
- P1: Charts in engagement/followers — SVGs need better aria-label with data context
- P1: QualityHeatmap date labels rotated 90° — screen reader unfriendly
- P2: FreshnessIndicator uses `title` not ARIA tooltip

## 5. Loading & Skeleton States
- loading.tsx exists with pulse skeletons for dashboard — good
- Missing: TrajectoryTimeline has no loading state for SSE connection
- Missing: No skeleton for engagement/followers pages (client-side, instant data)
- Gap spacing inconsistent: some gap-4, some gap-3

## 6. Form UX Issues
- No forms in Observatory (read-only dashboard) — N/A

## 7. Empty States
- Dashboard: basic "No agents registered" text — could be more prominent with CTA
- Content kanban: "Empty" per column — good
- Knowledge/Evaluations/Results: have empty states — good

## 8. Mobile/Responsive Issues
- P1: Agent detail table (6 columns) compresses severely on mobile
- P1: TopPostRow metrics (4 data columns) may wrap on small screens
- P1: QualityHeatmap forces horizontal scroll, cells still tiny
- OK: KPI cards use grid-cols-2 mobile → 4 desktop
- OK: Agent grid responsive 1-4 cols

## 9. Typography Scale
- P0: `text-[10px]` used in TopPostRow, engagement table, followers table — breaks design system
- P0: SVG `fontSize="10"` in GrowthChart, engagement chart — hardcoded, not responsive
- OK: text-2xl for KPI values, text-sm for labels, text-xs for subtitles

## 10. Top 10 P0/P1 Issues

### P0 (Critical)
1. **text-[10px] everywhere** | Files: TopPostRow.tsx:32, engagement/page.tsx, followers/page.tsx, results/page.tsx | Fix: Replace with text-xs (12px)
2. **Heatmap cells 20x20px** | File: QualityHeatmap.tsx | Fix: Increase to w-8 h-8 (32px) minimum, add tooltip
3. **Missing aria-labels on About social links** | File: about/page.tsx:170-180 | Fix: Add aria-label to each icon button
4. **Hardcoded hex colors in SVG charts** | Files: engagement/page.tsx, followers/page.tsx, GrowthChart.tsx | Fix: Use CSS vars or Tailwind color classes
5. **Inline backgroundColor in follower bars** | File: followers/page.tsx | Fix: Use Tailwind bg- classes

### P1 (High)
6. **No hover/focus states on interactive cards** | Files: KPICard.tsx, AgentCard.tsx, PlatformCard.tsx | Fix: Add hover:shadow-md, focus:ring-2
7. **SVG font labels hardcoded 10px** | Files: GrowthChart.tsx, engagement/page.tsx | Fix: Use responsive text or increase to 11-12px
8. **Agent detail table mobile compression** | File: agents/[id]/page.tsx | Fix: Hide low-priority columns on mobile or use card layout
9. **No Recharts for proper charts** | All chart components | Fix: Replace hand-rolled SVG with Recharts (already in package.json)
10. **TrajectoryTimeline no loading/error state** | File: TrajectoryTimeline.tsx | Fix: Add connection status indicator
