# Spec 031: LinkedIn Content Pipeline — Stage 1

**Status:** implemented
**Phase:** Phase 1
**Author:** Juan
**Created:** 2026-03-19
**Updated:** 2026-03-19

## Problem

The marketing agent (SPEC-010) exists but has no connected content pipeline. It can observe, reason, and generate content in isolation, but it cannot:
1. Read real analytics from social-media-automatization (via MCP)
2. Decide what to post based on actual performance data
3. Generate LinkedIn-specific content using authority engine (SPEC-017)
4. Queue posts for human approval before publishing

The result: Holus is a marketing brain without hands. It decides in a vacuum.

## Goals

- Marketing agent calls `social-media-mcp.get_analytics(days=7)` and receives real performance data
- Marketing agent calls `social-media-mcp.get_top_posts(limit=5)` to see what worked
- Marketing agent reads `config/products.yaml` to understand what to promote
- Marketing agent produces a `ContentDecision` with: product, platform="linkedin", content_type, hook, reasoning
- Content generation uses authority engine (written-authority specialist) to produce LinkedIn text posts
- Generated posts are queued via `social-media-mcp.schedule_post()` with `approval_required=true`
- Human reviews and approves/rejects via Observatory or Telegram
- All decisions logged to `trajectory.jsonl` for self-improvement

## Non-Goals

- Instagram, TikTok, X (Stage 2+)
- Image generation via pilaster (Stage 2)
- Video generation via genpeli (Stage 2)
- Auto-publishing without approval (Phase 2+)
- Multi-language content (Stage 3, SPEC-016)

## Solution

Wire the existing OBSERVE → REASON → ACT → EVALUATE loop to real MCP tools:

```
OBSERVE:
  → social-media-mcp: get_analytics(days=7) → AnalyticsReport
  → social-media-mcp: get_top_posts(limit=5) → list[Post]
  → Read config/products.yaml → list[Product]
  → Read agentic/memory/MEMORY.md → learned patterns

REASON (Claude Opus):
  → Analyze: which product has news? which content type performs best?
  → Output: ContentDecision(product, platform="linkedin", content_type, hook, reasoning)

ACT:
  → Authority engine generates LinkedIn post (written-authority specialist)
  → Quality gate: JudgeAgent evaluates output
  → social-media-mcp: schedule_post(content, platform="linkedin", approval_required=true)

EVALUATE:
  → Log decision + outcome to trajectory.jsonl
  → JudgeAgent scores content quality
  → Next cycle reads trajectory for pattern learning
```

## Implementation Notes

### OBSERVE step changes (`agent.py`)

```python
async def observe(self, state: dict) -> dict:
    # Call MCP tools
    analytics = await self.mcp.call("social-media", "get_analytics", days=7)
    top_posts = await self.mcp.call("social-media", "get_top_posts", limit=5)

    # Read product config
    products = yaml.safe_load((self.config.config_dir / "products.yaml").read_text())

    # Read memory
    memory = (self.config.data_dir / "MEMORY.md").read_text() if (self.config.data_dir / "MEMORY.md").exists() else ""

    state["analytics"] = analytics
    state["top_posts"] = top_posts
    state["products"] = products
    state["memory"] = memory
    return state
```

### REASON step (existing, needs LinkedIn-specific prompting)

The reasoning prompt should include:
- Analytics summary (impressions, engagement, top-performing content types)
- Product updates (what's new in pilaster/genpeli/invoz)
- Memory patterns (what worked before)
- Output: ContentDecision Pydantic model

### ACT step changes

```python
async def act(self, state: dict) -> dict:
    decisions = state["content_decisions"]
    generated = []

    for decision in decisions:
        if decision.platform != "linkedin":
            continue

        # Generate via authority engine
        content = await self.generate_linkedin_post(decision)

        # Quality gate
        score = await self.judge.evaluate(content, content_type="linkedin_post")
        if score < 0.7:
            continue  # Below quality threshold

        # Queue for approval
        result = await self.mcp.call("social-media", "schedule_post",
            content=content,
            platform="linkedin",
            approval_required=True,
        )

        generated.append({
            "platform": "linkedin",
            "text": content,
            "quality_score": score,
            "schedule_result": result,
        })

    state["generated_content"] = generated
    return state
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Analytics window | 7 days | Balances recency with sample size |
| Top posts limit | 5 | Enough to spot patterns without noise |
| Quality threshold | 0.7 | JudgeAgent score, prevents low-quality posts |
| approval_required | true | Phase 1: all posts need human review |
| Content types | tutorial, tips, case_study, announcement | From config/products.yaml |

### Dependencies

- Depends on: SPEC-010 (Marketing Agent), SPEC-017 (Authority Engine)
- Depends on: social-media-mcp server running with `get_analytics`, `get_top_posts`, `schedule_post` tools
- Depended on by: SPEC-016 (Multi-platform, bilingual — Stage 2+)

## Acceptance Criteria

- [ ] `social-media-mcp.get_analytics(days=7)` returns real data (mocked in tests)
- [ ] `social-media-mcp.get_top_posts(limit=5)` returns real data (mocked in tests)
- [ ] `config/products.yaml` is read and parsed correctly
- [ ] `ContentDecision` includes product, platform="linkedin", content_type, hook, reasoning
- [ ] Generated LinkedIn post uses authority engine framing (first person, expertise-led)
- [ ] JudgeAgent scores the post; posts below 0.7 are not queued
- [ ] `social-media-mcp.schedule_post()` is called with `approval_required=true`
- [ ] Decision is logged to `trajectory.jsonl` with all context
- [ ] `uv run pytest -q` passes with 1068+ tests after changes
- [ ] All E2E tests mock MCP calls and verify the full OBSERVE→REASON→ACT→EVALUATE loop

## Edge Cases & Failure Modes

- **MCP server down:** Observe step returns empty analytics. Reason step uses fallback strategy (promote newest product update from git log).
- **No product updates:** Reason step generates a "tips" or "tutorial" post instead of an announcement.
- **Quality gate rejects all content:** Log to trajectory as "quality_below_threshold" and skip ACT step. Don't force bad content.
- **social-media-mcp schedule_post fails:** Log error, retry once, then abort and alert.

## Rollback Plan

All changes are additive to existing marketing agent. Rollback = revert the git commits. No data migration needed. MCP tools are read-only (analytics) or gated (schedule_post requires approval).
