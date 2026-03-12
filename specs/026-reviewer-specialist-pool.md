# SPEC-026: Reviewer Specialist Pool — Category-Routed Content Review

## Problem

Content quality review is currently a single-pass generic check. We need a pool of 50+ specialist reviewers, each expert in a specific dimension (brand voice, visual composition, hook strength, CTA clarity, typography, color theory, etc.). For any piece of content, a category router selects ~4 relevant specialists who review independently, score, and provide improvement notes. Every reviewer has a unique ID, full observability, and can be individually evaluated against real engagement data.

## Architecture

```
Content created by specialist creator
        ↓
  Category Selector
  (maps content_type + platform → reviewer IDs)
        ↓
  ┌─────────────────────────────────────────────┐
  │ Selected Reviewers (4 per content piece)    │
  │                                             │
  │  reviewer-brand-tone-001  → score + notes   │
  │  reviewer-visual-comp-003 → score + notes   │
  │  reviewer-hook-qual-007   → score + notes   │
  │  reviewer-cta-clarity-002 → score + notes   │
  └─────────────────────────────────────────────┘
        ↓
  Aggregator: weighted average score + combined notes
        ↓
  Pass/fail against adaptive threshold
        ↓
  If pass → publish. If fail → notes feed back to creator for retry.
```

## The Review Flow (per reviewer)

Adapted from the /ux skill's deterministic pattern:

### Step 1: See Criteria (deterministic)
The reviewer loads its scoring rubric from its YAML config. This is NOT AI judgment — it's a predefined checklist specific to this reviewer's domain.

### Step 2: See Content
The reviewer receives:
- The generated content (text, image URL, or both)
- The target platform + format
- The creator specialist ID that made it
- The content brief/topic

For image content: the reviewer actually **sees the image** (multimodal). Not just metadata.

### Step 3: Score
Each reviewer outputs a structured score:
```json
{
  "reviewer_id": "reviewer-hook-qual-007",
  "content_id": "content-20260312-abc123",
  "scores": {
    "overall": 78,
    "dimension_1": 85,
    "dimension_2": 72,
    "dimension_3": 80
  },
  "pass": true,
  "notes": [
    "Hook is strong — question format grabs attention",
    "Could improve: the stat '40% → 87%' needs source attribution for credibility",
    "CTA is implicit — consider adding explicit next step"
  ],
  "improvement_suggestions": [
    "Add '(based on 500 posts analyzed)' after the stat",
    "Add 'Save this for your next campaign' as closing CTA"
  ],
  "confidence": 0.82,
  "review_time_ms": 3200
}
```

### Step 4: Log Everything
Every review is logged to Langfuse with:
- reviewer_id
- content_id
- creator_id (who made the content)
- scores (all dimensions)
- notes + suggestions
- review_time_ms
- later: correlated with real engagement data

## Reviewer YAML Config Format

Each reviewer is a YAML file in `config/reviewers/`:

```yaml
# config/reviewers/builtin/hook-quality.yaml
id: reviewer-hook-qual-001
name: Hook Quality Specialist
version: 1
category_tags:
  - text_post
  - carousel
  - quote_card
  - diagram
platforms:
  - all  # or specific: [instagram, twitter, linkedin]
description: >
  Evaluates the opening hook — first 2 lines of text or visual focal point.
  Does it stop the scroll? Does it create curiosity or emotional response?

scoring_rubric:
  dimensions:
    - name: scroll_stop_power
      weight: 0.4
      criteria: "Would this make someone stop scrolling in a feed of 100 posts?"
    - name: curiosity_gap
      weight: 0.3
      criteria: "Does the hook create a question the viewer needs answered?"
    - name: emotional_trigger
      weight: 0.2
      criteria: "Does it evoke an emotion (surprise, recognition, aspiration)?"
    - name: clarity
      weight: 0.1
      criteria: "Is the hook immediately understandable in under 2 seconds?"

prompt_template: |
  You are a Hook Quality Specialist reviewing social media content.

  ## Your Scoring Rubric
  {rubric}

  ## Content to Review
  Platform: {platform}
  Format: {content_type}
  Text: {text}
  Image: {image_url}

  ## Instructions
  1. Read the rubric dimensions carefully
  2. Examine the content (text AND image if present)
  3. Score each dimension 0-100
  4. Calculate weighted overall score
  5. Write 2-3 specific notes on what works and what doesn't
  6. Provide 1-2 concrete improvement suggestions

  Output JSON only.

# Evaluation tracking
created_at: "2026-03-12"
total_reviews: 0
avg_score_given: null
correlation_with_engagement: null  # updated after real data comes in
```

## Category Router

```python
# src/content_factory/review_router.py

class ReviewRouter:
    """
    Maps content_type + platform → set of reviewer IDs.
    Selects ~4 reviewers per content piece from the pool.
    """

    # Category mapping: content_type → required reviewer categories
    CATEGORY_MAP = {
        "carousel": ["visual_composition", "hook_quality", "brand_tone", "readability"],
        "text_post": ["hook_quality", "brand_tone", "cta_clarity", "emotional_resonance"],
        "quote_card": ["visual_composition", "hook_quality", "typography", "brand_tone"],
        "diagram": ["visual_composition", "data_clarity", "brand_tone", "readability"],
        "video_brief": ["hook_quality", "narrative_structure", "cta_clarity", "brand_tone"],
        "stat_card": ["data_clarity", "visual_composition", "hook_quality", "credibility"],
        "meme": ["humor_timing", "cultural_relevance", "brand_tone", "visual_composition"],
    }

    # Platform overrides: swap/add reviewers for platform-specific concerns
    PLATFORM_OVERRIDES = {
        "twitter": {"add": ["brevity_check"], "remove": []},
        "instagram": {"add": ["visual_composition"], "remove": ["brevity_check"]},
        "linkedin": {"add": ["professional_tone"], "remove": ["humor_timing"]},
    }
```

## Reviewer Categories (initial pool — 50+ reviewers across these categories)

| Category | # Reviewers | What They Check |
|----------|-------------|-----------------|
| hook_quality | 5 | Scroll-stopping power, curiosity gap, emotional trigger |
| visual_composition | 5 | Layout balance, visual hierarchy, whitespace, focal point |
| brand_tone | 4 | Voice consistency, personality match, authenticity |
| typography | 3 | Font size, readability, hierarchy, contrast |
| color_theory | 3 | Color harmony, emotional association, accessibility |
| cta_clarity | 3 | Clear next step, urgency, value proposition |
| data_clarity | 3 | Stat presentation, sourcing, visual representation |
| readability | 3 | Grade level, sentence length, jargon avoidance |
| emotional_resonance | 3 | Aspiration, recognition, motivation, relatability |
| cultural_relevance | 3 | Trending awareness, meme literacy, audience fit |
| narrative_structure | 3 | Story arc, payoff, pacing |
| credibility | 3 | Source attribution, claim verification, authority signals |
| platform_native | 4 | Platform-specific best practices (one per major platform) |
| accessibility | 2 | Alt text, contrast, screen reader friendliness |
| brevity_check | 2 | Word economy, redundancy, tightness |
| humor_timing | 2 | Comedic structure, audience-appropriate humor |
| professional_tone | 2 | LinkedIn-appropriate language, value framing |

**Total: ~53 specialist reviewers**

## Observability & Evaluation

### Per-Review Logging (Langfuse)
Every single review is a Langfuse trace:
```
trace_id: review-{content_id}-{reviewer_id}
metadata:
  reviewer_id: reviewer-hook-qual-001
  reviewer_version: 1
  content_id: content-20260312-abc123
  creator_id: specialist-carousel-001
  content_type: carousel
  platform: instagram
  scores: {overall: 78, scroll_stop: 85, curiosity: 72, ...}
  pass: true
  review_time_ms: 3200
```

### Reviewer Performance Tracking
After engagement data comes in (from analytics warehouse), correlate:
- Reviewer A approved → content got 500 views, 3% engagement → A was RIGHT
- Reviewer B rejected → we published anyway (override) → content got 2000 views → B was WRONG
- Track: precision, recall, F1 per reviewer over time
- Reviewers with low correlation → retrain (update prompt) or retire

### Combination Tracking
Track which SETS of 4 reviewers produce the best outcomes:
```json
{
  "combination_id": "combo-001",
  "reviewers": ["hook-qual-001", "visual-comp-003", "brand-tone-002", "cta-clarity-001"],
  "content_type": "carousel",
  "uses": 45,
  "avg_engagement_of_approved": 4.2,
  "avg_engagement_of_rejected": 1.8,
  "discrimination_ratio": 2.33
}
```

## Existing Code (EXTEND, don't rebuild)

The reviewer infrastructure already exists:
- `src/holus/agents/marketing/reviewers.py` — 4 working reviewers (brand, fact, compliance, engagement)
- `src/holus/agents/marketing/models.py` — ReviewResult, ReviewIssue Pydantic models (lines 282-303)
- `src/holus/agents/marketing/content_loop.py` — calls `run_all_reviewers()` (lines 242-253)
- `src/holus/agents/marketing/specialist_registry.py` — YAML loading, scoring, retirement pattern

## Files to Create

### New Files
- `src/holus/agents/marketing/review_router.py` — Category selection + reviewer dispatch
- `src/holus/agents/marketing/reviewer_pool.py` — Extends specialist_registry pattern for reviewers
- `src/holus/agents/marketing/review_aggregator.py` — Elevation rules, cross-category synthesis
- `config/reviewers/builtin/` — 15-20 seed reviewer YAML files (extending beyond the 4 hardcoded ones)
- `config/reviewers/spawned/` — Empty dir for AI-generated reviewers (Phase 3)

### Modified Files
- `src/holus/agents/marketing/content_loop.py` — Replace `run_all_reviewers()` with `review_router.review()`
- `src/holus/agents/marketing/reviewers.py` — Refactor 4 existing reviewers into YAML configs
- `config/review_categories.yaml` — Category → reviewer mapping config

## Integration with Content Loop (spec 025)

```
content_loop.py:
  1. Pick topic
  2. Route to creator specialist
  3. Creator produces content
  4. → review_router.select_reviewers(content_type, platform)
  5. → Run 4 reviewers in parallel (each sees content + image)
  6. → review_aggregator.aggregate(reviewer_results)
  7. → Check against adaptive_threshold
  8. If pass: publish via social-media MCP
  9. If fail: feed improvement_suggestions back to creator, retry once
  10. Log everything to Langfuse
```

## Phase Plan

### Phase 1: Wire + Review (this spec)
- ReviewRouter, ReviewerPool, ReviewAggregator
- 15-20 seed reviewer YAMLs
- Integration with content_loop
- Langfuse logging for every review

### Phase 2: Correlate with Engagement (after analytics warehouse is live)
- Pull engagement data from social-media-automatization analytics API
- Calculate reviewer accuracy (precision/recall vs real engagement)
- Track combination effectiveness

### Phase 3: Self-Improving Reviewers
- Auto-adjust reviewer prompts based on accuracy metrics
- Spawn new reviewers for gap categories
- Retire consistently inaccurate reviewers
- A/B test reviewer combinations
