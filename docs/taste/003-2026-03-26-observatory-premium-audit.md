# Taste Verdict 003: Observatory Dashboard Premium Audit

**Date:** 2026-03-26 | **Team:** Taste | **CID:** TASTE-20260327-168d52ed

## Artifact
The Holus Observatory dashboard — a Next.js frontend that monitors a 32-agent federated AI marketing system. Evaluated from codebase (design tokens, component structure, microcopy, brand system) rather than live screenshot.

## Composite Taste Score: 7/10

| Consultant | Score | Key Finding |
|------------|-------|-------------|
| visual-designer | 7/10 | Strong design token foundation (oklch heatmap, proper dark-first palette), but page headings are undersized and surface layering lacks depth |
| content-critic | 7/10 | Vocabulary is genuinely strong ("Inference Feed", "observing/reasoning/fault"), but subtitles describe features instead of narrating capability |
| brand-strategist | 7/10 | Signals "senior engineer's internal tool" — technically credible but one notch below "product-grade portfolio piece" |

## Verdict

### What It Looks/Sounds/Signals Like Now
- **Visual:** A well-crafted internal monitoring tool — closer to Grafana's modern dark theme than to Linear Analytics. Design token system is Vercel-grade, but compositional execution (type scale, surface depth, logo distinctiveness) is conservative.
- **Content:** A thoughtful engineering team's dashboard — technically precise domain vocabulary, but the narrative layer is missing. Subtitles are feature lists, not capability statements. Empty states speak developer-to-developer.
- **Brand:** Senior engineer's production tool, circa 2025-2026. Amber brand is distinctive (most AI dashboards default to blue/purple). Signals technical credibility but not yet "product" — more GitHub Copilot Metrics than Linear Analytics.

### What It Should Look/Sound/Signal Like
- **Visual:** Linear's Analytics dashboard — where headings command the page at 32px+, surfaces create depth through layered cards, and the dark palette uses 3+ surface tones for visual hierarchy. The quality heatmap (oklch interpolation) is already at this level.
- **Content:** Honeycomb's dashboard copy — where every label teaches you something about the system. Subtitles should narrate capability ("32 agents observing, reasoning, acting — tracked in real time") not list features ("Live agent activity, quality drift, and system-wide KPIs").
- **Brand:** A polished AI infrastructure product dashboard — the kind of thing someone at Anthropic would screenshot and share internally. Weights & Biases or Honeycomb level — tools built by infrastructure engineers that look like products.

## Top 3 Fixes (Priority Order)

1. **Rewrite the page subtitle from feature-list to capability-statement** — content-critic lens, highest impact. Change "Live agent activity, quality drift, and system-wide KPIs" to "32 agents observing, reasoning, acting — tracked in real time." This turns description into narrative, teaches the architecture, and creates a hook. Also change footer from "Read-only" to "Observing 32 agents across 3 silos."
2. **Scale up page headings to 32px font-bold and add brand accent** — visual-designer lens. The current 24px heading is undersized for a dashboard hero. Add a subtle amber dot or gradient underline beneath the heading to establish visual authority. This is the single highest-impact visual change.
3. **Add a hero metric treatment to the most important KPI** — brand-strategist lens. Make "Mean judge score" or "Cycle success rate" 2x larger than the other KPIs with a subtle radial gradient background. This creates a focal point and signals product thinking — internal tools never prioritize one metric visually.

## Dissent
The current restrained approach has a genuine advantage: it looks like a real working tool, not a marketing mockup. Over-polishing risks undermining the "this person actually built and operates a 32-agent system" authenticity signal. The raw technical voice in empty states ("No agents registered in AGENTS.yaml") could be seen as a feature — it says "I'm an engineer, not a designer pretending to be one." The counter-argument is that the best infrastructure tools (Linear, Vercel, Honeycomb) prove you can be both authentic AND polished.

## Action Items
- [ ] Rewrite subtitle: "Live agent activity, quality drift, and system-wide KPIs" → "32 agents observing, reasoning, acting — tracked in real time"
- [ ] Rewrite footer: "Read-only" → "Observing 32 agents across 3 silos"
- [ ] Increase page heading from text-2xl (24px) to text-3xl (32px) with tracking-tight
- [ ] Add amber accent element (dot or gradient underline) to page headings
- [ ] Create hero KPI treatment — make lead metric 2x size with subtle radial gradient
- [ ] Add surface-3 token (#1a2744 or similar) for nested cards to increase depth
- [ ] Rewrite empty states from error-language to system-language
- [ ] Rewrite OG description from feature list to value proposition
