# Taste Recheck 002: Holus Observatory Frontend

**Date:** 2026-03-26 | **Team:** Taste | **Prior:** [001-2026-03-26](001-2026-03-26-observatory-frontend.md) (score: 5/10)

## Artifact
The Holus Observatory frontend after major improvements: design token system, Tremor/Recharts integration, amber brand identity, custom SVG logo, animated ReAct loop diagram, custom tooltips, accessible heatmap, skeleton loading, and dark scrollbar styling.

---

## Composite Taste Score: 7.8/10

| Dimension | Score | Prior | Delta | Summary |
|-----------|-------|-------|-------|---------|
| 1. Visual Craft | 8 | ~6.5 | +1.5 | Token system is now comprehensive and mostly enforced. Typography hierarchy is tight. Card system with hover elevation is polished. |
| 2. Data Visualization | 8 | ~4 | +4 | Tremor AreaChart, BarChart, SparkBarChart all wired up. Custom heatmap with hover tooltips. Pillar progress bars. Major leap. |
| 3. Dark Mode | 7 | ~5.5 | +1.5 | Surface layers, border tiers, and semantic colors are well-structured. But ~40 raw Tailwind color classes remain across 4 files. |
| 4. Brand Identity | 7 | ~5 | +2 | Amber palette is distinctive. Custom SVG logo with concentric rings is excellent. But OG image is a 1x1 pixel placeholder. |
| 5. Content/Copy | 8.5 | ~6 | +2.5 | "Inference Feed", "Quality Signals", "Agent Fleet", "Stage gates from draft to publish" -- this is observatory vocabulary, not template copy. |
| 6. Micro-interactions | 8 | ~4 | +4 | Stagger animations, page transitions, status pulses, card hover elevation, sidebar nav hover, reduced-motion support. Strong. |

---

## Dimension-by-Dimension Analysis

### 1. Visual Craft -- 8/10

**What improved:** The design token system in `globals.css` is now comprehensive -- 5 surface tiers, 3 text tiers, 3 border tiers, semantic colors with subtle variants, spacing tokens, transition tokens, shadow tokens. The `.card` / `.card-interactive` utility classes give a consistent card language across the app. Typography uses Plus Jakarta Sans + JetBrains Mono -- a strong pairing. Section headings, KPI cards, agent cards, and tables all share a coherent visual rhythm.

**What prevents a 9:** The `content/page.tsx` status count cards use inline rounded-xl + inline styles rather than the `.card` class, creating a subtle visual inconsistency (no hover elevation, no shared border radius token). Some pages use `className="px-6 py-6"` hardcoded while others use `style={{ padding: 'var(--page-padding)' }}` -- this inconsistency means changing the page padding token only affects some pages.

**Fix to reach 10:**
- Replace all hardcoded `px-6 py-6` with `style={{ padding: 'var(--page-padding)' }}` across content, evaluations, knowledge, and health pages.
- Apply `.card` class to the status count cards on the content page and the freshness summary cards on the knowledge page.
- Add a `.section-title` utility class (text-lg font-bold + text-primary) so page titles don't repeat the same inline styles on every page.

### 2. Data Visualization -- 8/10

**What improved:** This was the single biggest leap. Tremor `AreaChart` for follower growth and engagement trends. Tremor `BarChart` for platform distribution and daily net change. Tremor `SparkBarChart` for agent quality sparklines. The custom `QualityHeatmap` has proper hover tooltips (not native `title` attributes), keyboard navigation via arrow keys, and an accessible `role="grid"` structure. Progress bars for pillar and product breakdowns are clean.

**What prevents a 9:** All Tremor charts use `colors={['amber']}` or `colors={['emerald']}` -- single-color charts. The engagement page chart shows one metric at a time via radio toggle, but there is no multi-series overlay (e.g., impressions vs. engagement rate on dual axes). The heatmap cells are solid-color blocks (green/yellow/red) with no gradient -- a continuous color scale from red through amber to green would communicate quality drift more precisely.

**Fix to reach 10:**
- Add a continuous color scale to `QualityHeatmap` using `oklch()` interpolation from `--danger` through `--warning` to `--success`, mapping 0-10 linearly. Reserve the flat `var(--surface-2)` only for "no data" cells.
- Add a dual-axis chart option on the engagement page: impressions area + engagement rate line overlaid, using two y-axes. Tremor supports `categories={['Impressions', 'Eng. Rate']}`.
- Add `yAxisWidth` and `tickGap` props to Tremor charts to prevent axis label overlap at small viewport widths.

### 3. Dark Mode -- 7/10

**What improved:** The `.dark` class in `globals.css` maps all tokens to the brand-visual.yaml dark theme values. Surface layers (#0A0F1E -> #0F172A -> #1a1a24) create proper depth. Dark scrollbar styling. Semantic colors have dark-appropriate subtle backgrounds using `rgba()`. The `@media (prefers-color-scheme: dark)` fallback handles auto-detection.

**What prevents a 9:** There are still approximately 40 raw Tailwind color classes across 4 files that bypass the token system:
- `ContentKanban.tsx`: 14 instances (`bg-blue-100`, `bg-purple-100`, `bg-green-100`, `bg-red-100`, `text-red-600 dark:text-red-400`, `bg-gray-100`, etc.)
- `ContentDetailPanel.tsx`: 12 instances (status colors, verdict colors, button colors, error styling)
- `health/page.tsx`: 10 instances (overall status card with `bg-green-50 dark:bg-green-950`, dot colors)
- `evaluations/page.tsx`: 3 instances (verdict badge colors)

These create a two-system problem: some components use tokens, others use raw Tailwind `dark:` prefixes. In dark mode, these raw classes still work, but they form a parallel color system that cannot be updated from a single source.

**Fix to reach 10:**
- Define semantic CSS custom properties for pillar colors (engineering/blue, building-in-public/purple, bilingual/orange, systems/cyan) in `globals.css`, then reference them via inline styles instead of Tailwind class strings.
- Define `--verdict-pass-bg`, `--verdict-pass-text`, `--verdict-fail-bg`, `--verdict-fail-text` (etc.) tokens in both `:root` and `.dark`, then replace all `bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300` patterns with inline style references.
- Replace the health page overall-status card with the same pattern used on the dashboard page (inline styles + `var(--success-subtle)` / `var(--warning-subtle)` / `var(--danger-subtle)`).
- Replace `bg-blue-600 hover:bg-blue-700` on the Schedule button with `background: var(--info)` or a dedicated `--button-schedule` token.

### 4. Brand Identity -- 7/10

**What improved:** The amber/gold palette is distinctive -- it immediately differentiates from the blue/purple default of every other Tailwind dashboard. The `HolusLogo` SVG with concentric dashed-outer, solid-middle, filled-core rings is a genuine identity mark, not a placeholder icon. The logo semantics (observe/reason/act rings) tie directly to the system architecture. The animated ReAct loop diagram on the About page is a strong hero element. OG meta tags are defined in `layout.tsx` with proper title, description, and image reference.

**What prevents a 9:** The `og-image.png` is a **1x1 pixel transparent PNG** (70 bytes). This means every LinkedIn/Slack/Twitter share shows either nothing or a broken preview. The favicon/app icon situation is unclear -- there is no `favicon.ico` or `apple-touch-icon.png` in the public directory, only default Next.js SVGs. The "Built by" footer section on the About page is the only place the creator's identity appears -- there is no branded wordmark treatment for "Holus Observatory" beyond plain text.

**Fix to reach 10:**
- Generate a real OG image (1200x630): dark navy background (#0A0F1E), the concentric-ring logo mark at left, "Holus Observatory" in Plus Jakarta Sans Bold at right, "32-agent federated AI system" subtitle, amber accent line. This is the single highest-ROI fix for external perception.
- Add a `favicon.ico` (32x32) and `apple-touch-icon.png` (180x180) derived from the concentric-ring logo, using amber on dark navy.
- Consider rendering the "Holus Observatory" sidebar header using the logo + a styled wordmark rather than two separate `<div>` elements.

### 5. Content/Copy -- 8.5/10

**What improved:** This dimension saw perhaps the most meaningful improvement. Every page title and subtitle now uses observatory/diagnostic vocabulary:
- "Inference Feed" (not "Dashboard")
- "Quality Signals" with "Judge verdicts and quality drift across 7 domain-expert evaluators"
- "Stage gates from draft to publish -- click any card to inspect, calibrate, or reject"
- "Audience interaction signals -- impressions, reactions, and engagement rate by channel"
- "Acquisition, churn, and net growth trajectory by channel"
- "Learned patterns, strategy memory, and extracted lessons from evaluation cycles"
- Agent statuses use domain vocabulary: "observing", "reasoning", "evaluating", "fault", "offline"

Empty states are also well-handled: "No agents in registry. Verify AGENTS.yaml is populated and Observatory API is reachable." -- this is actionable, not generic.

**What prevents a 9:** The tooltip content on some elements is sparse. The model tier badge says `title="Model tier used for inference"` -- good. But the KPI cards have no tooltips explaining what the metric means or how it is calculated. "Cycle success rate" -- success by what definition? "Mean judge score" -- weighted how? The About page technical stack section lists values but does not explain why those choices were made (a missed opportunity to signal engineering judgment).

**Fix to reach 10:**
- Add descriptive `title` tooltips to all KPI cards explaining the metric definition: e.g., "Percentage of observe-reason-act cycles that completed without error in the last 7 days" for "Cycle success rate".
- Add a brief "Why this stack" annotation on the About page: e.g., "JSONL + YAML (no database)" could have a subtitle "Eliminates ops overhead -- entire system state is git-trackable".
- Add copy for the empty state on the Engagement page when demo data is present but no real data exists, signaling "Demo data shown -- connect social-media MCP for live signals."

### 6. Micro-interactions -- 8/10

**What improved:** Another major leap. The system now has:
- **Stagger animations:** 12-step fade-in-up keyframe with 50ms increments for card grids
- **Page transitions:** `page-enter` keyframe on every page wrapper
- **Card hover:** `card-interactive` class with border color shift to brand, shadow elevation, and subtle translateY(-1px)
- **Sidebar nav:** Smooth background/color transitions via `nav-link` class
- **Status pulses:** `status-pulse` keyframe on active agent dots and live stream indicator
- **ReAct loop:** Continuously rotating orbit ring, step-scale transitions on click, traveling pulse dot
- **Heatmap:** Custom tooltip that follows cursor position relative to grid container
- **Focus rings:** Consistent `focus-ring` utility class with brand-colored outline on all interactive elements
- **Reduced motion:** Full `prefers-reduced-motion` media query disabling all animations

**What prevents a 9:** The sidebar mobile slide-over uses only `transform transition-transform` -- there is no backdrop fade-in animation or staggered content reveal. The trajectory timeline rows use inline `onMouseEnter`/`onMouseLeave` to set background color -- this works but does not animate because `transition-colors` is on the element while the style change is programmatic. The ContentDetailPanel slide-over has no entry animation -- it appears instantly. Radio group option transitions are limited to a color swap with no scale or background-fill effect.

**Fix to reach 10:**
- Add a slide-in animation to the `ContentDetailPanel`: transform translateX(100%) to translateX(0) with a 200ms ease-out. Add a backdrop fade from transparent to `var(--surface-overlay)`.
- Add a mobile sidebar backdrop opacity animation: `opacity: 0` to `opacity: 1` with 200ms transition when `open` changes.
- Replace the trajectory timeline's programmatic hover with a CSS-only hover using a class like `hover:bg-[var(--surface-2)]` (already used on the evaluations table -- just apply consistently).
- Add a subtle scale(1.02) to the RadioGroup selected option for a more tactile feel.

---

## Prior Action Items -- Status

| Action Item (from 001) | Status | Notes |
|------------------------|--------|-------|
| Audit all components: replace every raw Tailwind color with CSS custom property | Partial | ~80% done. Sidebar, KPI, Agent, Growth, Platform, System Health, TopPost, Pillar all use tokens. ContentKanban, ContentDetailPanel, health/page, evaluations/page still have ~40 raw Tailwind classes. |
| Fix font variable mismatch | Done | `@theme` now references `--font-plus-jakarta`, layout loads Plus Jakarta Sans, body font-family is correct. |
| Fix `loading.tsx` referencing non-existent `dark:bg-gray-850` | Done | Loading now uses `.skeleton` and `.skeleton-card` CSS classes with token-based colors. |
| Fix `QualityHeatmap.tsx` providing no mode differentiation | Done | Heatmap now uses `var(--surface-2)`, `var(--success)`, `var(--warning)`, `var(--danger)` -- no raw Tailwind classes. Custom tooltip replaces native title. |
| Replace `GrowthChart.tsx` hand-rolled SVG with Tremor AreaChart | Done | Uses Tremor `AreaChart` with `colors={['amber']}`. |
| Replace agent detail div-bar sparkline with Tremor SparkBarChart | Done | `AgentSparkline` uses Tremor `SparkBarChart`. |
| Add hover tooltips to QualityHeatmap | Done | Custom floating tooltip with agent name, date, score, positioned relative to grid container. Keyboard-navigable. |
| Design OG image (1200x630) | Not done | `og-image.png` is a 1x1 pixel placeholder (70 bytes). |
| Choose signature accent color outside blue/purple | Done | Amber (#F59E0B primary, #FBBF24 accent) with deep navy background. |
| Add animated ReAct loop diagram to About page hero | Done | Interactive circular diagram with rotating orbit, traveling pulse dot, step highlighting on click/auto-cycle. |

---

## Top 3 Fixes (Priority Order)

### 1. Replace OG image placeholder with a real 1200x630 asset
**Impact:** Brand Identity 7 -> 9. Every LinkedIn/Slack share currently shows nothing. A proper OG image is the single highest-ROI fix for external perception. This is the one thing a recruiter will see before they even click the link.
**Effort:** Low (one static image).
**Spec:** Dark navy background (#0A0F1E), concentric-ring logo mark at left, "Holus Observatory" in Plus Jakarta Sans Bold, "32-agent federated AI system" subtitle, amber accent line, viewport dimensions 1200x630.

### 2. Eliminate remaining ~40 raw Tailwind color classes in ContentKanban, ContentDetailPanel, health/page, evaluations/page
**Impact:** Dark Mode 7 -> 9. The token system is already built -- these are the last holdouts from the pre-improvement era. They create a parallel color system that cannot be centrally controlled.
**Effort:** Medium (define ~6 new semantic tokens in globals.css, then find-and-replace in 4 files).
**Files:** `ContentKanban.tsx`, `ContentDetailPanel.tsx`, `health/page.tsx`, `evaluations/page.tsx`.

### 3. Add entry/exit animations to ContentDetailPanel slide-over and standardize page padding
**Impact:** Visual Craft 8 -> 9, Micro-interactions 8 -> 9. The detail panel appearing instantly breaks the otherwise smooth animation language. Inconsistent padding tokens make the system feel like two different developers worked on it.
**Effort:** Low-medium (one animation keyframe, one padding token audit).

---

## Overall Assessment

The Observatory has gone from a 5/10 "well-intentioned internal dashboard" to a 7.8/10 product that reads as deliberate, branded, and architecturally sophisticated. The amber identity, concentric-ring logo, observatory vocabulary, Tremor chart integration, and animation system collectively signal "full-stack AI engineer with product taste" -- which is exactly the target positioning.

The remaining gaps are mechanical, not conceptual. The design system is the right design system; it just needs to be enforced in the last 4 files. The OG image is the right idea; it just needs to be a real image. The animations are the right animations; they just need to cover the slide-over panel.

One more improvement cycle of this caliber puts the Observatory at 9+, which is "would forward the link to the eng manager" territory.
