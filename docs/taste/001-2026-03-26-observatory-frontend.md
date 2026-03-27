# Taste Verdict 001: Holus Observatory Frontend

**Date:** 2026-03-26 | **Team:** Taste | **CID:** TASTE-20260326-bcb84759

## Artifact
The Holus Observatory frontend — a Next.js 16 dark-mode dashboard for monitoring an autonomous AI marketing strategist. Evaluated: all components, pages, design system, data visualizations, dark mode execution.

## Composite Taste Score: 5/10

| Consultant | Score | Key Finding |
|------------|-------|-------------|
| visual-designer | 5.3/10 (avg: 6.5 overall, 4 data viz, 5.5 dark mode) | Token system is Linear-quality but half the app ignores it. Tremor + Recharts installed but never used. |
| content-critic (Gemini) | 6/10 | Generic "Dashboard" copy — should sound like a high-fidelity control room, not a Vercel template |
| brand-strategist | 5.25/10 (avg: 5.5 positioning, 5 recruiter) | Indigo-on-dark is the Helvetica of AI dashboards — signals Tailwind defaults, not deliberate design |

## Verdict

### What It Looks/Sounds/Signals Like Now
- **Visual:** A well-intentioned internal dashboard that is 60% of the way to polished. The token system and sidebar feel like they came from someone who studied Linear. The content/evaluations/health pages feel like a different developer copy-pasted Tailwind dark mode patterns.
- **Brand:** Competent side-project dashboard by someone who knows React and Tailwind. "Built during a weekend" tier. Visually indistinguishable from a ShadCN/Tailwind starter template.

### What It Should Look/Sound/Signal Like
- **Visual:** Linear's settings page, Vercel's analytics dashboard, Railway's project view. One surface color system, 4-5 type sizes used consistently, cards with subtle borders and hover elevation.
- **Brand:** Full-stack AI engineer with product taste who builds systems AND cares about how they present. The artifact that makes a recruiter forward the link to the design-aware eng manager.

## Top 3 Fixes (Priority Order)

1. **Enforce design token system** — Replace ALL raw Tailwind color classes (`text-gray-X`, `bg-gray-X`, `dark:*`) with existing CSS custom properties. The token system is already well-designed — it just isn't used consistently. ~8 files to touch. This alone takes the score from 5 to 7+. (visual-designer, HIGH confidence)

2. **Wire up Tremor/Recharts** — Replace hand-rolled SVG charts and div-bar "sparklines" with Tremor `AreaChart`, `SparkAreaChart`, `BarChart`. The dependencies are already installed. Current data viz scores 4/10 and having unused chart libraries in package.json signals cargo-culting. (visual-designer, HIGH confidence)

3. **Create distinctive visual signature** — Replace generic indigo-on-dark palette with a unique accent color outside the saturated blue/purple spectrum (amber/gold or deep teal). Design a proper OG image (1200x630) for LinkedIn/Slack sharing. Add animated ReAct loop diagram to About page hero. (brand-strategist, HIGH confidence)

## Dissent
Both specialists agreed on the core issue (token inconsistency) but the brand-strategist raised a valid caution: *"Over-investing in visual polish before the system produces real, demonstrable marketing results could make the Observatory feel like a 'pretty empty dashboard' — which is worse than an ugly dashboard with real data."* The visual-designer countered that the fix is mechanical (find-and-replace), not a redesign, so the risk is low.

## Action Items
- [ ] Audit all components: replace every raw Tailwind color class with CSS custom property equivalents
- [ ] Fix font variable mismatch: `@theme` references `--font-geist-sans` but layout loads Plus Jakarta Sans
- [ ] Fix `loading.tsx` referencing non-existent `dark:bg-gray-850`
- [ ] Fix `QualityHeatmap.tsx` where `text-gray-400 dark:text-gray-400` provides no mode differentiation
- [ ] Replace `GrowthChart.tsx` hand-rolled SVG with Tremor `AreaChart`
- [ ] Replace agent detail div-bar sparkline with Tremor `SparkAreaChart`
- [ ] Add hover tooltips to QualityHeatmap (replace native title attribute)
- [ ] Design OG image (1200x630) with dashboard screenshot + Holus wordmark
- [ ] Choose signature accent color outside blue/purple spectrum
- [ ] Add animated ReAct loop diagram to About page hero
