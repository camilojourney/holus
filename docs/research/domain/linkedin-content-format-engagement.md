---
last_updated: 2026-03-27
review_cadence: 30d
next_review: 2026-04-26
---

# Research: What content formats get the most engagement on LinkedIn for AI engineers in 2026?

## Options Compared

| Format | Avg Engagement Rate | Reach Multiplier | Dwell Time | Best For | Risk |
|--------|-------------------|------------------|------------|----------|------|
| **Document/PDF Carousel** | 6.60-7.00% [VERIFIED] | 3.4x vs single image [UNVERIFIED] | 30-60s per post [UNVERIFIED] | Educational content, tutorials, step-by-step guides | Production cost (design needed) |
| **Native Video (<90s)** | 5.60-6.00% [VERIFIED] | 5x vs text for awareness [UNVERIFIED] | Variable | Demos, personality, behind-the-scenes | 36% YoY view growth BUT reach metrics contradictory |
| **LinkedIn Live** | 29.6% [UNVERIFIED] | Highest of any format | Duration of stream | Real-time interaction, AMAs | Requires scheduling, audience commitment |
| **Text-Only** | 2-4.5% [VERIFIED] | Baseline | 5 seconds avg [UNVERIFIED] | Hot takes, quick insights, storytelling | Lowest engagement but lowest effort |
| **Polls** | 4.20-4.40% [VERIFIED] | 200%+ above average reach [UNVERIFIED] | Low (single click) | Community engagement, question-driven content | Least used, engagement is shallow (clicks not comments) |
| **Single Image + Text** | 4.85-5.30% [VERIFIED] | 1x baseline | ~10s | Quick visual, infographic | Declining performance |

## Key Data Points

### SocialInsider 2026 Benchmarks (Most Reliable Source) [VERIFIED]

| Format | Engagement Rate | YoY Change |
|--------|----------------|------------|
| Native Documents | 7.00% | +14% |
| Multi-Image | 6.45% | slight decrease |
| Video | 6.00% | +7% |
| Images | 5.30% | +9% |
| Text | 4.50% | +12% |
| Polls | 4.20% | N/A |
| Links | 3.25% | N/A |

Platform average: 5.20% (+8% YoY) [VERIFIED]

### Carousel Optimization [UNVERIFIED]

- 7-slide carousels perform 18% better than any other length
- 10-slide carousels have 22% higher reach than 3-slide
- Beyond 15 slides, completion rates drop 40%
- Carousels are the most saved post type on LinkedIn
- Target save-to-impression ratio: at least 0.5%

### Algorithm Signals (2026) [VERIFIED where noted]

- Comments weighted 15x more than likes [UNVERIFIED — widely cited but no primary LinkedIn source]
- First 60 minutes critical — only 5% of underperforming posts recover [UNVERIFIED]
- External links reduce reach by 60% [UNVERIFIED — consistent across all sources]
- Posts aligned with creator's verified expertise get 40% higher impressions [UNVERIFIED]
- Content lifespan extended to 2-3 weeks (was 24 hours) [UNVERIFIED]
- Responding to comments within 15 minutes: 90% algorithmic boost [UNVERIFIED]

### AI Content Performance [VERIFIED — Originality.ai study]

- 65% of Tech & AI LinkedIn posts are AI-generated (sample: 3,368 posts, 99 profiles)
- In Tech & AI niche: AI posts get +7% more engagement (302 vs 282 avg)
- In Marketing & Branding: human posts outperform AI by 73%
- Overall: human-written content outperforms AI in 7 of 11 industries

### Platform-Wide Decline [UNVERIFIED]

- Views down 50% YoY
- Engagement down 25% YoY
- Follower growth down 59% YoY
- Makes format selection even more critical — marginal differences matter more

## Recommendation

**For Holus: Lead with Document/PDF Carousels (60%), supplement with Text posts (30%), and Polls (10%).**

The data overwhelmingly favors document/carousel posts for AI engineering content on LinkedIn:

1. **Highest engagement rate** — 7.00% native documents vs 4.50% text [VERIFIED via SocialInsider]
2. **Highest dwell time** — 30-60 seconds vs 5 seconds for text [UNVERIFIED], which is the algorithm's primary quality signal
3. **Educational content match** — Holus promotes AI tools (Pilaster, genpeli, invoz). Tutorials and how-tos map perfectly to carousel format
4. **Most saved format** — saves extend content lifespan beyond the initial distribution window [UNVERIFIED]

**Video should be used selectively, not as the primary format.** Despite growing views, video has contradictory reach data and requires significantly higher production cost. Use video for:
- Product demos (genpeli video editing demos are natural video content)
- Behind-the-scenes of AI systems
- Short clips (<60 seconds) repurposed from longer content

**Text posts remain valuable** for thought leadership, hot takes on AI news, and quick insights. They require minimal production time and the 4.50% engagement rate is still competitive.

## Decision Points

DECISION_POINT: primary_content_format
OPTIONS: A) Document/PDF Carousels — highest engagement (7.00%), best dwell time, ideal for tutorials B) Native Video — growing viewership, best for demos and personality, higher production cost C) Text-only — lowest friction, moderate engagement, best for hot takes and news commentary
RECOMMENDATION: A
CONFIDENCE: HIGH
EVIDENCE: [VERIFIED] SocialInsider 2026 benchmarks show native documents at 7.00% vs video 6.00% vs text 4.50%

DECISION_POINT: content_mix_ratio
OPTIONS: A) 60-30-10 (carousel-text-polls) — recommended by postiv.ai B) 50-30-20 (carousel-video-text) — video-heavy approach C) 40-40-20 (carousel-text-video) — balanced approach
RECOMMENDATION: A
CONFIDENCE: MEDIUM
EVIDENCE: [UNVERIFIED] 60-30-10 split cited by postiv.ai. No A/B test data found. Holus should track and adjust.

DECISION_POINT: posting_frequency
OPTIONS: A) 3-5 posts/week — moderate, sustainable for AI agent B) Daily — aggressive, +5,001 impressions/post at 6-10/week C) 2-3 posts/week — conservative, quality-focused
RECOMMENDATION: A
CONFIDENCE: MEDIUM
EVIDENCE: [UNVERIFIED] postiv.ai data shows increasing returns up to 11+/week, but quality maintenance is key. 3-5/week balances output with Holus's silo dependencies.

DECISION_POINT: ai_vs_human_content_voice
OPTIONS: A) AI-generated with human review — Holus drafts, Juan approves/edits B) Fully AI-generated — Holus posts autonomously C) Human-written, AI-assisted — Juan writes, AI optimizes
RECOMMENDATION: A
CONFIDENCE: HIGH
EVIDENCE: [VERIFIED] Originality.ai study shows only +7% engagement for AI content in tech (negligible), but -73% in marketing. Hybrid approach with human voice editing (already implemented in Holus spec 032 Humanization Gate) is safest.

## Adversary Analysis

### Strongest argument AGAINST the recommendation

The carousel-first strategy relies heavily on SECONDARY sources — marketing tool vendors selling carousel creation products (PostNitro, UseVisuals, Postiv.ai). These sources have direct financial incentive to inflate carousel performance. The SocialInsider data (most credible) shows a narrower gap: documents at 7.00% vs video at 6.00% — only a 17% difference, not the 278% cited by other sources. The real advantage may be modest, not dramatic.

### What makes us regret this in 6 months?

1. **LinkedIn algorithm shift to video.** LinkedIn is investing heavily in video (LinkedIn Video tab launched 2025, 36% YoY view growth). If the algorithm pivots to favor video like Instagram did with Reels, carousel-optimized content loses its edge overnight.
2. **Carousel fatigue.** If 60% of LinkedIn content becomes carousels (as the 60-30-10 rule proliferates), the format loses its novelty advantage. The current high engagement may reflect scarcity, not inherent superiority.
3. **AI content detection.** As AI detection improves, algorithmically-generated carousels may be penalized. LinkedIn already labels AI content. If detection triggers reach reduction, Holus's output gets throttled.
4. **Production bottleneck.** Carousels require visual design. Holus depends on Pilaster for image generation. If Pilaster's visual quality doesn't match professional carousel standards, the format advantage is wasted on poor execution.

### What are we not seeing? (confirmation bias check)

- No gatherer found data on **newsletter** or **article** performance — LinkedIn Newsletters reportedly get direct email push to subscribers, potentially bypassing the feed algorithm entirely.
- No data on **collaborative articles** — one early source mentioned 12.3% engagement rate for collaborative articles, but this was not verified and may be invitation-only.
- The entire research assumes feed-based distribution. **Direct messaging** and **LinkedIn groups** are alternative distribution channels with different engagement dynamics.

### Risk matrix

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Algorithm pivot to video-first | HIGH | MEDIUM | Keep 20-30% video in mix; monitor algorithm signals monthly |
| Carousel format fatigue | MEDIUM | HIGH | Differentiate with technical depth, not just format; animated infographics (spec 033) |
| AI content detection penalty | MEDIUM | LOW | Humanization Gate (spec 032) already in place; maintain human review |
| Pilaster visual quality insufficient | HIGH | MEDIUM | A/B test Pilaster visuals vs Canva/manual; set minimum quality threshold |
| Data sources biased (tool vendors) | MEDIUM | HIGH | Track Holus's own engagement data; compare to SocialInsider benchmarks quarterly |

### Missing evidence

- **No primary LinkedIn source.** All data comes from third-party analytics tools and blogs. LinkedIn's own engineering blog does not publish format-specific engagement benchmarks.
- **No AI engineer-specific data.** All benchmarks are platform-wide averages. AI/ML engineers may engage differently than marketing professionals or recruiters.
- **No A/B test data.** No source provided controlled experiments comparing formats with identical content. The engagement differences may reflect content quality differences, not format advantages.
- **No data on LinkedIn Newsletter performance** — a potentially underexplored format for Holus.

## Discarded Claims

> [PHANTOM] "LinkedIn uses LLM-powered expert knowledge scoring" — URL https://almcorp.com/blog/linkedin-feed-algorithm-update-llm-2026/ did not render article content (JS-only page). Claim demoted to [UNVERIFIED] in main analysis.

## Contradictions Between Sources

| Metric | Source A | Source B | Resolution |
|--------|---------|---------|------------|
| Carousel engagement rate | 24.42% (meet-lea.com) | 7.00% (SocialInsider) | SocialInsider is more credible (analytics platform vs tool vendor). Use 7.00%. |
| Video reach trend | "Growing 2x faster than other formats" (dataslayer) | "Reach dropped 200% compared to 2024" (postiv.ai) | Likely measuring different things: views growing, but reach/impressions per post declining. |
| Poll engagement | 8.9% (meet-lea.com) | 4.20% (SocialInsider) | Use SocialInsider's 4.20% — more conservative and from analytics platform. |
| Text engagement | 2-4% (dataslayer) | 4.50% (SocialInsider) | Use SocialInsider's 4.50% — more recent and methodologically rigorous. |

## Sources

1. [SocialInsider LinkedIn Benchmarks 2026](https://www.socialinsider.io/social-media-benchmarks/linkedin) — PRIMARY, analytics platform, [VERIFIED]
2. [Originality.ai LinkedIn AI Study](https://originality.ai/blog/linkedin-ai-study-engagement) — PRIMARY, original research (3,368 posts), [VERIFIED]
3. [Dataslayer — LinkedIn Algorithm Feb 2026](https://www.dataslayer.ai/blog/linkedin-algorithm-february-2026-whats-working-now) — SECONDARY, [VERIFIED]
4. [Postiv.ai — LinkedIn Content Strategy 2025](https://postiv.ai/blog/linkedin-content-strategy-2025) — SECONDARY, [VERIFIED]
5. [GrowLeads — Text vs Video 2026](https://growleads.io/blog/linkedin-algorithm-2026-text-vs-video-reach/) — SECONDARY, [VERIFIED]
6. [UseVisuals — Carousel Stats 2026](https://usevisuals.com/blog/linkedin-carousel-engagement-statistics-2026) — SECONDARY, [VERIFIED]
7. [Meet Lea — Engagement Metrics 2026](https://meet-lea.com/en/blog/linkedin-engagement-metrics-benchmarks) — SECONDARY, [VERIFIED]
8. [PostNitro — Carousel Stats 2025](https://postnitro.ai/blog/post/linkedin-carousel-engagement-stats-2025) — SECONDARY, [VERIFIED]
9. [UseVisuals — Algorithm Updates 2026](https://usevisuals.com/blog/linkedin-algorithm-updates-for-2026) — SECONDARY, content not fully verifiable
10. [ALM Corp — LinkedIn LLM Algorithm](https://almcorp.com/blog/linkedin-feed-algorithm-update-llm-2026/) — PHANTOM (page did not render)
