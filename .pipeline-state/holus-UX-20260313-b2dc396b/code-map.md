# UX Code Map — Holus Observatory — holus-UX-20260313-8b2ad5fe

## 1. Routes & Pages

| Route | File | Type |
|-------|------|------|
| `/` | `src/app/page.tsx` | Dashboard — KPIs, agent grid, trajectory timeline, top posts |
| `/about` | `src/app/about/page.tsx` | Recruiter landing — hero, agent loop, products, tech stack |
| `/agents` | `src/app/agents/page.tsx` | Agent grid with search/filter |
| `/agents/[id]` | `src/app/agents/[id]/page.tsx` | Agent detail — scores, config, history |
| `/content` | `src/app/content/page.tsx` | Content pipeline kanban (draft/review/published) |
| `/engagement` | `src/app/engagement/page.tsx` | Engagement tracker — charts, platform filter, KPIs |
| `/followers` | `src/app/followers/page.tsx` | Follower tracker — growth chart, daily bars, platform table |
| `/evaluations` | `src/app/evaluations/page.tsx` | Quality heatmap + evaluation records |
| `/knowledge` | `src/app/knowledge/page.tsx` | Knowledge files browser |
| `/health` | `src/app/health/page.tsx` | Service health status |
| `/results` | `src/app/results/page.tsx` | Campaign results |

## 2. Button & Touch Target Audit (file:line, h-* class, px size)

- `src/components/QualityHeatmap.tsx:70` — heatmap cells `w-7 h-7` (28px) — still below 44px WCAG target, but acceptable for dense data grids
- `src/app/engagement/page.tsx:141` — platform filter buttons `px-3 py-1.5` (~30px height) — below 44px minimum
- `src/app/followers/page.tsx:140` — platform filter buttons `px-3 py-1.5` (~30px height) — below 44px minimum
- `src/app/agents/page.tsx` — search input and filter buttons need height audit
- `src/components/Sidebar.tsx` — nav items need min-height 44px check

## 3. Color & Theme Issues (file:line, exact value, replacement)

- `src/app/engagement/page.tsx:10-15` — hardcoded hex `platformColors` (`#2563eb`, `#ec4899`, `#0ea5e9`, `#6b7280`, `#111827`) used in SVG `stroke` — acceptable for chart lines, but consider CSS custom properties
- `src/app/engagement/page.tsx:17-23` — `platformDarkColors` duplicates color definitions — should derive from one source
- `src/app/followers/page.tsx:9-15` — same `platformColors` hardcoded hex values
- `src/app/followers/page.tsx:54-55` — SVG `linearGradient` uses hardcoded `stopColor={color}` — acceptable for dynamic charts
- `src/app/engagement/page.tsx:123` — chart color fallback `'#6366f1'` hardcoded — use CSS var or Tailwind token
- `src/app/followers/page.tsx:123` — same `'#6366f1'` hardcoded
- `src/components/TrajectoryTimeline.tsx` — status dot colors use Tailwind classes (good)

## 4. Accessibility Gaps (file:line, what's missing)

- `src/app/engagement/page.tsx:138-149` — platform filter buttons missing `aria-pressed` for toggle state
- `src/app/engagement/page.tsx:152-164` — metric filter buttons missing `role="radiogroup"` and `aria-pressed`
- `src/app/followers/page.tsx:136-148` — platform filter buttons missing `aria-pressed`
- `src/app/about/page.tsx:241-249` — social links now have `aria-label` (FIXED in previous round)
- `src/components/QualityHeatmap.tsx:42-93` — heatmap grid missing `role="grid"` and `role="row"` semantics
- `src/app/engagement/page.tsx:52` — MiniChart SVG has `aria-label` (good)
- `src/app/followers/page.tsx:52` — GrowthLine SVG has `aria-label` (good)
- `src/components/Sidebar.tsx` — nav missing `aria-current="page"` on active item
- `src/app/content/page.tsx` — content cards missing `aria-label` descriptions

## 5. Loading & Skeleton States

- `src/app/page.tsx` — dashboard uses Suspense boundaries (good) but no skeleton placeholders
- `src/app/agents/page.tsx` — agent grid has no loading skeleton
- `src/app/evaluations/page.tsx` — heatmap has no loading state
- `src/app/content/page.tsx` — kanban has no loading skeleton
- `src/app/knowledge/page.tsx` — file list has no loading state
- **Pattern needed:** skeleton components for KPICard, AgentCard, table rows

## 6. Form UX Issues

- `src/app/agents/page.tsx` — search input: no clear button, no debounce indicator
- No other forms in the app (read-only dashboard)

## 7. Empty States

- `src/components/QualityHeatmap.tsx:34-40` — has empty state "No agent data available" (good)
- `src/components/TrajectoryTimeline.tsx` — has disconnected/empty state (good)
- `src/app/content/page.tsx` — kanban columns may have no items — needs empty column state
- `src/app/knowledge/page.tsx` — needs "No knowledge files" empty state
- `src/app/results/page.tsx` — needs "No results yet" empty state

## 8. Mobile/Responsive Issues

- `src/app/engagement/page.tsx:135-166` — filter buttons wrap well with `flex-wrap` (good)
- `src/app/engagement/page.tsx:169` — KPI grid `grid-cols-2 lg:grid-cols-5` (good)
- `src/app/engagement/page.tsx:206-247` — table uses `overflow-x-auto` (good)
- `src/app/followers/page.tsx:135` — platform filter `w-fit` may overflow on small screens
- `src/app/about/page.tsx:73` — max-w-4xl constrains width well
- `src/components/Sidebar.tsx` — sidebar may not collapse on mobile — needs responsive hamburger
- `src/app/agents/[id]/page.tsx` — agent detail table may overflow on mobile

## 9. Typography Scale

- All `text-xs` instances (12px) — acceptable minimum, previously fixed from `text-[10px]`
- `src/app/about/page.tsx:80` — h1 `text-4xl` (36px) — good hero size
- `src/app/engagement/page.tsx:128` — h1 `text-2xl` (24px) — good page title
- `src/app/about/page.tsx:198` — tech stack labels `text-xs` — borderline but acceptable
- Chart axis labels now use `text-xs` (fixed from `text-[10px]`)

## 10. Top 10 P0/P1 Issues (P0=conversion-blocking, P1=significant friction)

### P0 (Critical)
1. **No mobile sidebar collapse** | `src/components/Sidebar.tsx` | Sidebar is always visible — on mobile it blocks the entire viewport or pushes content off-screen
2. **Filter buttons below 44px touch target** | `src/app/engagement/page.tsx:141`, `src/app/followers/page.tsx:140` | `py-1.5` = ~30px, needs `py-2.5` minimum

### P1 (High friction)
3. **No loading skeletons anywhere** | All pages | Data-fetching pages show blank space then jump to content — jarring UX
4. **Platform filter missing aria-pressed** | `src/app/engagement/page.tsx:138`, `src/app/followers/page.tsx:136` | Screen readers can't tell which platform is selected
5. **Heatmap missing grid semantics** | `src/components/QualityHeatmap.tsx:42` | No `role="grid"` — inaccessible to screen readers
6. **Sidebar missing aria-current="page"** | `src/components/Sidebar.tsx` | Active page not announced to screen readers
7. **No hover/focus states on Explore cards** | `src/app/about/page.tsx:220` | Cards have `hover:border-indigo-300` but no focus ring for keyboard nav
8. **Engagement chart duplicate color maps** | `src/app/engagement/page.tsx:9-23` | `platformColors` and `platformDarkColors` should be unified
9. **Content pipeline empty column states** | `src/app/content/page.tsx` | Empty kanban columns show nothing — need "No items" message
10. **Daily net change bars no legend** | `src/app/followers/page.tsx:199-227` | Green/red bars have no visible legend — only tooltip on hover
