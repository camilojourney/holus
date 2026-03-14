# UX Fix Plan — Holus Observatory — holus-UX-20260313-b2dc396b

## Status: Most P0/P1 issues already fixed in prior rounds

Previous rounds fixed: mobile sidebar, aria-current, filter touch targets (py-2), radiogroup semantics, heatmap grid ARIA, focus rings on cards, color map dedup, daily net change legend, empty column states.

## P0 (Critical — none remaining)
All P0 issues fixed.

## P1 (High — 1 remaining)
- [x] **Heatmap header/cell width mismatch** | File: `src/components/QualityHeatmap.tsx:50,73` | Actual: header `w-5`, cells `w-7` | Fix: make headers `w-7` to match cells

## P2 (Medium — skip for now)
- [ ] **Loading skeletons** | All pages | No skeleton placeholders during data fetch
- [ ] **Dashboard KPI trend indicators** | `src/app/page.tsx` | No sparklines/arrows on KPI cards
- [ ] **Agent search input clear button** | `src/app/agents/page.tsx`

## P3 (Low — skip for now)
- [ ] **Chart tooltips** | Engagement + Followers sparklines have no hover tooltips

## Summary
- P0: 0 | P1: 1 | P2: 3 | P3: 1
- All 35 acceptance criteria met in current code
