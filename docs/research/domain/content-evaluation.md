---
title: Content Evaluation & Quality Gates
domain: content-quality
owner: holus-research
last_updated: 2026-03-17
review_cadence: 30
next_review: 2026-04-16
---

# Content Evaluation & Quality Gates

## Evaluation Architecture (3-Tier)

### Tier 1: Deterministic Quality Gate ($0, instant)

Applied in `quality_score.py` before content enters the queue.

| Check | Rule | Action |
|-------|------|--------|
| Character limits | Platform-specific (Twitter 280, LinkedIn 3000) | Block |
| Anti-pattern phrases | 13 phrases ("leverage synergies", "let's dive in") | Block |
| Forbidden topics | Trading, pythia, milo, financial advice | Block |
| Content pillar valid | Must match builder_stories/ai_frameworks/etc. | Block |
| Exclamation ratio | Max 3% | Block |
| Emoji ratio | Max 2% | Block |
| No leading "I" | First word cannot be "I" | Block |

Score 0-100. Threshold: 60. Below = auto-reject.

**File:** `src/holus/agents/marketing/quality_score.py` (270 lines)
**Status:** Wired and running.

### Tier 2: Constitutional AI Judge (~$0.002/eval, per-piece)

Independent LLM evaluation using Haiku. Different model from generator (Sonnet) to prevent circular self-congratulation.

**7 domain-expert evaluators** routed by content type:

| Evaluator | Content Types | Dimensions |
|-----------|--------------|------------|
| written-content-judge | text_post, thread, article | hook_strength, narrative_arc, voice_fidelity, authority_signal, readability |
| visual-content-judge | carousel, single_image | visual_hierarchy, brand_alignment, info_clarity, scroll_stop, pacing |
| video-content-judge | video_reel, video_script | hook_timing, pacing, retention_prediction, caption_quality, CTA_strength |
| engagement-judge | CTAs, growth content | conversion_potential, authenticity, brand_safety, audience_match, frequency |
| seo-judge | research, blog | keyword_relevance, search_intent, topical_authority, competitive_gap, uniqueness |
| platform-fit-judge | repurposed content | algorithm_signal, format_compliance, native_feel, timing |
| brand-safety-judge | ALL content (hard gate) | voice_deviation, anti_pattern_count, reputation_risk, forbidden_content |

**Routing:** `AgentRegistry.get_evaluator_for(content_type)` → returns relevant evaluators.
**Verdict:** PASS (≥0.8) / PARTIAL (0.5-0.8) / FAIL (<0.5)
**Model:** Haiku at temperature 0.0 (deterministic, independent from workers).

**File:** `src/holus/self_improvement/judge.py` (307 lines)
**Status:** Built. NOT wired into content pipeline (Sprint 1 priority).

### Tier 2b: Visual Judge (~$0.03/eval, for visual content)

Multimodal evaluation on rendered PNG. Text judge reads JSON; visual judge SEES the image.

| What it catches | Why text judge misses it |
|-----------------|-------------------------|
| Bad contrast (text invisible on gradient) | Text judge sees CSS values, not rendered result |
| Cramped layout (bullets overflow) | Text judge doesn't render HTML |
| Broken SVG (chart not displaying) | Text judge can't see images |
| Visual hierarchy (nothing guides the eye) | Requires spatial reasoning |

**Model:** Sonnet vision (or Haiku 3.5 vision for cost optimization).
**Input:** Rendered PNG from `PlaywrightEngine.render_spec()`.
**Output:** `{visual_hierarchy, brand_alignment, readability, scroll_stop_power, overall}` (0-1 each).

**Blended score:** `judge_score = 0.5 × text_score + 0.5 × visual_score`
For text-only content (no visual), only text judge runs.

**Status:** Not yet implemented. Sprint 1.2.

### Tier 3: Human Review

Content with any judge score goes through the human review queue. A passing score
does not authorize publication: dispatch still requires an immutable approved
review decision for the exact content revision.

Over time, as prompts evolve and quality improves, PARTIAL rate should decrease.

## Reward Signal Design

### Pre-publish reward: Judge score (proxy)
- Available immediately after generation
- Measures quality, not resonance
- Used as sole reward signal for first 100 observations

### Post-publish reward: Engagement signal (ground truth)
- Available 24-72h after publishing
- Platform-specific weights:

```python
REWARD_WEIGHTS = {
    "linkedin": {"comments": 0.4, "shares": 0.3, "likes": 0.2, "saves": 0.1},
    "instagram": {"saves": 0.4, "shares": 0.3, "comments": 0.2, "likes": 0.1},
    "tiktok":    {"watch_time": 0.5, "shares": 0.3, "comments": 0.2},
    "twitter":   {"retweets": 0.4, "quotes": 0.3, "replies": 0.2, "likes": 0.1},
}
```

### Blended reward (dynamic weighting)
- Days 1-30: `reward = judge_score` (no engagement data yet)
- After 100 paired observations: `reward = 0.3 × judge + 0.7 × engagement`
- Engagement is the real objective; judge is a proxy that decays in influence

### Drift detection
- Monitor 30-day moving average of blended reward
- If avg drops 0.1 from its peak → trigger prompt optimization
- Prevents slow quality degradation that failure streaks don't catch

## Judge Stability Policy

**Frozen for 90 days** from first activation. No optimization, no rubric changes.

After 90 days: epochal recalibration:
1. Run old + new judge on 50 pieces
2. Compute mapping function between scores
3. Apply to historical trajectory data
4. Switch to new judge version

**Why:** If the judge is optimized while prompt optimization uses judge scores as reward, you get a non-stationary optimization target (Goodhart's Law). The prompt optimizer chases a moving goalpost.

## Research References

- Anthropic, "Constitutional AI: Harmlessness from AI Feedback" (2022)
- Meta, "Self-Taught Evaluator" (2024) — LLM self-improvement without human labels
- G-Eval pattern — Chain-of-Thought before numeric scoring
- Holus ADR-0005: Agent self-improvement architecture decision
