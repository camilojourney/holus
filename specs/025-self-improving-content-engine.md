# Spec 025: Self-Improving Content Engine

**Status:** Not Started
**Phase:** Sprint 4
**Author:** Opus (VS Code orchestrator)
**Created:** 2026-03-11
**Updated:** 2026-03-11
**Depends on:** 024 (Content Factory v2 — modules built, not wired)

## Problem

Content Factory v2 (spec 024) built the components — 5 specialists, 5 framers, 4 reviewers, eval gate, MCP clients. But they're standalone modules, not a running system. There is no:

1. **Continuous loop.** Nothing triggers content creation automatically. No cron, no scheduler, no "run forever and keep posting."
2. **Specialist evolution.** The 5 specialists (carousel, PDF, diagram, video_brief, text) are hardcoded. The system can't discover that "stat cards with before/after numbers get 3x engagement" and spawn a new specialist optimized for that pattern.
3. **Format exploration.** The system only knows 5 formats. Real social media has dozens of content shapes — quote cards, news-style posts, tutorial threads, meme formats, image+text overlays, slideshow videos with music, voiceover clips. The system should discover and test new formats autonomously.
4. **Adaptive quality threshold.** The eval gate has a fixed pass/fail bar. It should start low (70) on test accounts and rise as the system proves itself.
5. **Real engagement feedback.** The eval gate scores content before posting using heuristics. It doesn't know if the content actually performed well. No post-publish measurement loop.
6. **A/B testing.** No mechanism to post two variants of the same idea and compare which performs better.

## Goals

- A continuous content loop (cron-triggered) that runs autonomously: observe → create → evaluate → post → measure → learn → repeat
- A specialist spawner that creates NEW specialist types based on engagement data and trend research
- An adaptive threshold that starts at 70 and auto-rises as quality improves
- Post-publish measurement that correlates internal scores with real engagement
- A/B variant testing on the 4 test accounts (2 EN, 2 ES)
- Web research integration to discover trending topics and new content formats
- Multi-modal content: text + AI images (Pilaster) + edited video (Genpeli) + music/voiceover combinations

## Non-Goals

- Building image rendering in Holus — Pilaster does AI images, that's it
- Building video editing in Holus — Genpeli does that
- Publishing logic — social-media-automatization is the dumb poster
- Posting to production accounts (camiloexperience, camilojourney) — test accounts only until threshold reaches 85+
- Trading content — permanently out of scope

## Architecture

```
                    ┌──────────────────────┐
                    │    CRON TRIGGER       │
                    │  (every 30 min)       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     OBSERVE          │
                    │  • analytics (MCP)   │
                    │  • web trends        │
                    │  • specialist scores │
                    │  • what hasn't been  │
                    │    tried yet         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     DECIDE           │
                    │  • pick product      │
                    │  • pick format       │
                    │  • pick specialist   │
                    │  • pick platform(s)  │
                    │  • A/B variant?      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     CREATE           │
                    │  • specialist writes │
                    │  • Pilaster: images  │
                    │  • Genpeli: video    │
                    │  • framer adapts     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     EVALUATE         │
                    │  score < threshold?  │
                    │  YES → feedback →    │
                    │        regenerate    │
                    │  NO → post           │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     POST             │
                    │  social-media MCP    │
                    │  test accounts only  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  MEASURE (24-72h)    │
                    │  • real engagement   │
                    │  • score correlation │
                    │  • format comparison │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     LEARN            │
                    │  • update weights    │
                    │  • spawn specialists │
                    │  • adjust threshold  │
                    │  • retire losers     │
                    └──────────┘
```

## Solution

### 1. Continuous Loop Runner

A new module `src/holus/agents/marketing/content_loop.py` that:

- Runs as a cron job (launchd plist, every 30 minutes)
- Each cycle: observe → decide → create → evaluate → post → log
- Tracks cycle history in `data/content-loop/cycles.jsonl`
- Respects kill switch — if `config/guardrails.yaml` kill_switch is ON, skip the cycle
- Budget cap: max $X/day on API calls (configurable in `config/base.yaml`)

```python
async def run_content_cycle() -> CycleResult:
    """One cycle of the content loop."""
    # 1. Check kill switch and budget
    # 2. Observe: analytics + trends + specialist leaderboard
    # 3. Decide: pick product × format × platform × specialist
    # 4. Create: specialist + visual layer + framer
    # 5. Evaluate: reviewers + eval gate (threshold from adaptive_threshold())
    # 6. If score < threshold: feedback → regenerate (max 3 attempts)
    # 7. Post to test accounts via social-media MCP
    # 8. Log cycle result to cycles.jsonl
    # 9. Return CycleResult for outer loop
```

### 2. Specialist Registry (Dynamic)

Replace the hardcoded `SPECIALIST_REGISTRY` dict with a dynamic registry:

```python
# config/specialists/
#   builtin/
#     carousel.yaml
#     text.yaml
#     pdf.yaml
#     diagram.yaml
#     video_brief.yaml
#   spawned/
#     stat_card_v1.yaml      # auto-created after discovering pattern
#     quote_card_v2.yaml     # evolved from v1 based on engagement
#     news_brief_v1.yaml     # spawned after web research found news format works
```

Each specialist YAML defines:
```yaml
name: stat_card_v1
format: image_text_overlay   # visual format
description: "Stats-focused card with before/after numbers"
created_at: 2026-03-11
created_by: spawner          # "builtin" or "spawner"
generation: 1                # incremented on evolution
parent: text                 # what it evolved from (null for builtins)
lifetime_score: 0.0          # avg engagement score, updated by learning loop
lifetime_posts: 0            # how many times used
retired: false               # set to true when a better version replaces it

system_prompt: |
  You create stat-focused social media content cards.
  Structure: hook stat (X% → Y%), 3 supporting bullets, closing insight.
  ...

output_schema: TextOutput    # which Pydantic model to validate against
platforms: [linkedin, instagram, facebook]
visual_layer: pilaster        # "pilaster" | "none" | "genpeli"
visual_prompt_template: |
  Dark professional background, large stat number {stat} in green,
  clean typography, {product_name} branding
```

### 3. Specialist Spawner

`src/holus/agents/marketing/specialist_spawner.py`

Runs after every N cycles (configurable, default 10). Analyzes:
- Which specialists have highest engagement?
- Which content patterns appear in top posts?
- What formats exist on social media that we haven't tried?
- Web research: what's trending in content creation?

Then:
1. **Mutate:** Take the best-performing specialist, tweak its prompt (different hook style, different structure, different tone) → save as `{name}_v{N+1}.yaml`
2. **Cross:** Combine traits from two high-performing specialists → new specialist
3. **Discover:** Web search for trending content formats → create specialist from scratch
4. **Retire:** Specialists with lifetime_score < threshold after 10+ posts → `retired: true`

```python
async def spawn_cycle(registry: SpecialistRegistry) -> list[SpecialistConfig]:
    """Analyze performance, spawn new specialists, retire losers."""
    top_performers = registry.get_top(n=3, min_posts=5)
    low_performers = registry.get_bottom(n=3, min_posts=10)

    new_specialists = []

    # Mutate top performers
    for spec in top_performers:
        variant = await mutate_specialist(spec, strategy="vary_hook_style")
        new_specialists.append(variant)

    # Cross top performers
    if len(top_performers) >= 2:
        cross = await cross_specialists(top_performers[0], top_performers[1])
        new_specialists.append(cross)

    # Web research for new formats
    trends = await research_content_trends()
    for trend in trends[:2]:
        novel = await create_specialist_from_trend(trend)
        new_specialists.append(novel)

    # Retire low performers
    for spec in low_performers:
        if spec.lifetime_score < registry.retirement_threshold:
            registry.retire(spec.name)

    return new_specialists
```

### 4. Adaptive Threshold

```python
# data/content-loop/threshold.json
{
    "current_threshold": 70,
    "history": [
        {"date": "2026-03-11", "threshold": 70, "reason": "initial"},
        {"date": "2026-03-18", "threshold": 73, "reason": "avg_score_above_80_for_7_days"}
    ],
    "rules": {
        "raise_by": 3,
        "raise_when": "avg_internal_score > current + 10 for 7 consecutive days",
        "lower_by": 2,
        "lower_when": "post_rate < 1_per_day for 3 consecutive days",
        "ceiling": 90,
        "floor": 60
    }
}
```

The threshold auto-adjusts:
- **Rises** when the system consistently scores well above the bar (quality improving)
- **Drops** when the system can't produce enough content (bar too high, starving the learning loop)
- **Never above 90** on test accounts (save 95+ for production graduation)
- **Never below 60** (basic quality floor)

### 5. Post-Publish Measurement

After posting, a delayed measurement job runs (24h and 72h marks):

```python
async def measure_post_performance(post_id: str) -> PerformanceResult:
    """Called 24h and 72h after posting."""
    analytics = await social_media_client.get_post_analytics(post_id)
    return PerformanceResult(
        post_id=post_id,
        impressions=analytics.impressions,
        engagement_rate=analytics.engagement_rate,
        likes=analytics.likes,
        comments=analytics.comments,
        shares=analytics.shares,
        internal_score=cycle_log[post_id].eval_score,
        score_correlation=correlate(internal_score, engagement_rate),
    )
```

This data feeds back into:
- Specialist leaderboard (which specialist creates the best-performing content)
- Reviewer calibration (if internal score poorly predicts engagement, adjust reviewers)
- Format leaderboard (which formats get the most engagement per platform)

### 6. A/B Testing

When the system creates content, it can optionally create a variant:

```python
async def create_ab_variant(original: ContentPiece) -> ContentPiece:
    """Create a variant for A/B testing."""
    strategy = random.choice([
        "different_hook",        # same body, different opening
        "different_format",      # same idea, carousel vs text
        "different_specialist",  # same idea, different specialist
        "different_image",       # same text, different Pilaster prompt
    ])
    return await create_variant(original, strategy)
```

Post variant A to EN test account, variant B to ES test account (or vice versa). Compare after 72h.

### 7. Visual Layer Integration

Holus doesn't render anything. It calls tools:

| Visual need | Tool | How |
|-------------|------|-----|
| AI-generated image | Pilaster MCP | `generate(prompt, template, character)` |
| Image for carousel slides | Pilaster MCP | One generation per slide |
| Video from raw footage | Genpeli REST | `process_video(urls, instruction)` |
| Image slideshow + music | Genpeli REST | `process_video(image_urls, "create slideshow with music")` |
| Voiceover | Future TTS integration | Text → speech → combine with images in Genpeli |
| No visual needed | None | Text-only post |

The specialist decides the visual layer. The specialist YAML has a `visual_layer` field that determines which tool to call.

### 8. Web Research Integration

Every N cycles, Holus searches the web for:
- Trending topics in AI, tech, content creation
- New content format ideas (what are creators doing?)
- Competitor analysis (what's working for similar accounts?)
- News that's relevant to Pilaster/Genpeli/Invoz

This feeds into both content ideas AND specialist spawning.

### 9. Test Account Strategy

| Account | Platform | Language | Purpose |
|---------|----------|----------|---------|
| camilonation | Instagram | EN | A/B testing (variant A) |
| cmadapt | Instagram | ES | A/B testing (variant B) |
| camilonation-page | Facebook | EN | Volume testing |
| cmadapt-page | Facebook | ES | Volume testing |

**Graduation criteria:** When a specialist consistently produces content scoring 85+ internally AND getting above-median engagement on test accounts for 2+ weeks → it's eligible for production accounts.

### 10. Multi-Modal Combinations

Each cycle, the system tracks which combinations have been tried:

```python
# data/content-loop/combination-log.jsonl
{"combo": "text+pilaster_image+linkedin", "count": 15, "avg_engagement": 3.2}
{"combo": "carousel+pilaster_slides+instagram", "count": 8, "avg_engagement": 5.1}
{"combo": "text_only+facebook", "count": 22, "avg_engagement": 1.8}
{"combo": "video_brief+genpeli+instagram", "count": 0, "avg_engagement": null}  # untested!
```

The decision engine prioritizes **untested combinations** — every cycle should try something new. The exploration rate decays over time as the system converges on what works.

## Implementation Plan

### Phase 1: Wire + Loop (build now)
1. Wire Content Factory v2 modules into `content_loop.py`
2. Dynamic specialist registry (load from YAML files)
3. Adaptive threshold (start at 70)
4. Cron trigger (launchd plist, every 30 min)
5. Cycle logging to `data/content-loop/cycles.jsonl`
6. Post to test accounts via social-media MCP

### Phase 2: Measure + Learn (build after Phase 1 posts 20+ times)
7. Post-publish measurement (24h + 72h)
8. Specialist leaderboard
9. Format leaderboard
10. Reviewer calibration

### Phase 3: Evolve (build after Phase 2 has 1 week of data)
11. Specialist spawner (mutate, cross, discover)
12. A/B testing
13. Web research integration
14. Combination exploration tracking
15. Specialist retirement

### Phase 4: Expand (build after Phase 3 proves itself)
16. Voiceover integration (TTS)
17. Music overlay via Genpeli
18. Production account graduation
19. New product accounts (Pilaster-specific, Genpeli-specific)

## Data Files

| File | Purpose |
|------|---------|
| `data/content-loop/cycles.jsonl` | Every cycle logged (append-only) |
| `data/content-loop/threshold.json` | Current threshold + history |
| `data/content-loop/combination-log.jsonl` | What combos have been tried |
| `data/content-loop/specialist-scores.json` | Leaderboard |
| `data/content-loop/measurement-queue.json` | Posts awaiting 24h/72h measurement |
| `config/specialists/builtin/*.yaml` | Hardcoded specialist prompts |
| `config/specialists/spawned/*.yaml` | Auto-generated specialist prompts |

## Models

```python
class CycleResult(BaseModel):
    cycle_id: str
    timestamp: datetime
    product: str
    format: ContentFormat
    specialist: str
    platforms: list[str]
    eval_score: float
    threshold: float
    posted: bool
    post_ids: list[str]  # from social-media MCP
    attempts: int  # how many regenerations before passing
    variant_of: str | None  # A/B testing reference
    combination: str  # e.g. "carousel+pilaster_slides+instagram"

class SpecialistConfig(BaseModel):
    name: str
    format: str
    description: str
    created_at: datetime
    created_by: Literal["builtin", "spawner"]
    generation: int
    parent: str | None
    lifetime_score: float
    lifetime_posts: int
    retired: bool
    system_prompt: str
    output_schema: str
    platforms: list[str]
    visual_layer: Literal["pilaster", "genpeli", "none"]
    visual_prompt_template: str | None

class PerformanceResult(BaseModel):
    post_id: str
    measured_at: datetime
    impressions: int
    engagement_rate: float
    likes: int
    comments: int
    shares: int
    internal_score: float
    score_correlation: float  # how well internal score predicted engagement
```

## Test Accounts (Connection IDs)

```python
TEST_ACCOUNTS = {
    "en_instagram": {
        "account_id": "17841427829926095",
        "name": "camilonation",
    },
    "es_instagram": {
        "account_id": "17841448898103111",
        "name": "cmadapt",
    },
    "en_facebook": {
        "account_id": "931545820053163",
        "name": "camilonation-page",
    },
    "es_facebook": {
        "account_id": "306293825881155",
        "name": "cmadapt-page",
    },
}
```

API details:
- Endpoint: `POST /api/v1/publish`
- Use `platforms: ["instagram"]` or `platforms: ["facebook"]`
- Use `account_id` field to target specific test account
- Customer ID: `cust_01KK0W2BCSH21HVBPQN6BDQS70`

## Verification

- `uv run pytest -q` — all tests pass
- `uv run ruff check .` — no lint errors
- Content loop can run one cycle end-to-end with mock MCP clients
- Specialist registry loads builtin YAMLs
- Adaptive threshold adjusts based on simulated scores
- Cycle results logged correctly to JSONL
