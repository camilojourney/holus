# Holus Architecture

**What Holus is:** An AI marketing strategist agent that promotes the product portfolio.
It decides what content to create, calls specialized silo tools to produce it,
and learns from results to improve strategy over time.

**What Holus is not:** A unified codebase that replaces the individual repos.
Not a trading system. Not a content publisher. Not a video generator.
Those are silos. Holus uses them as tools.

**Last updated:** 2026-02-25
**Update cadence:** Only on major structural changes.

---

## Mental Model

```
                        HOLUS
                  (marketing strategist)
                          |
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    genpeli-mcp    social-media-mcp   pilaster-mcp
    (make videos)  (post + analytics) (make images)
          │               │               │
          ▼               ▼               ▼
       genpeli      social-media-    pilaster.ai
                    automatization
```

Holus holds the BRAIN (strategy, decisions, learning).
The silos hold the HANDS (execution, data, publishing).

Data never flows back into Holus permanently.
Holus reads silo data to make decisions, but the source of truth stays in the silo.

---

## The Agent Loop (ReAct)

Holus runs as an episodic agent — triggered weekly by cron or manually via Telegram.

```
OBSERVE
  → call social-media-mcp: get_analytics(last_7_days)
  → read config/products.yaml: what is new in Pilaster, genpeli, invoz?
  → read .self-improvement/MEMORY.md: what have we learned?

REASON  (Claude Opus — strategy decisions)
  → "Tutorial posts outperform promo posts 4:1"
  → "Pilaster shipped workflow diff view — good tutorial topic"
  → "LinkedIn performing better than Instagram for this audience"
  → "This week: create ComfyUI diff tutorial targeting LinkedIn + TikTok"

ACT
  → call pilaster-mcp: generate_image(brief="workflow diff comparison screenshot")
  → call genpeli-mcp: create_video(brief="...", images=[...], voice="camilo")
  → call social-media-mcp: schedule_post(video_url, platforms=["linkedin","tiktok"])

EVALUATE
  → log what was decided and why → .self-improvement/memory/trajectory.jsonl
  → write weekly report → .self-improvement/reports/marketing/YYYY-MM-DD.md

NEXT CYCLE
  → analytics from this week's posts feed into next week's OBSERVE
```

---

## Silo Architecture

Each silo is an independent repo that owns its own data and execution.
Holus communicates with silos via MCP (Model Context Protocol) tool calls.

### genpeli (video creation silo)

**What it owns:** Video generation pipeline, prompt versioning, eval framework.
**What Holus calls:**
```python
genpeli.create_video(brief: str, style: str, voice: str) → VideoResult
genpeli.get_job_status(job_id: str) → JobStatus
```
**Data stays in:** genpeli's own Postgres + R2 storage.

### social-media-automatization (publishing + analytics silo)

**What it owns:** All social media accounts, posting queue, platform analytics.
**What Holus calls:**
```python
social_media.schedule_post(content, platforms, scheduled_at) → PostResult
social_media.get_analytics(days: int, platform: str) → AnalyticsReport
social_media.get_top_posts(limit: int, metric: str) → List[Post]
```
**Data stays in:** social-media-automatization's own database.
**Analytics live here, not in Holus.** Holus reads them, never stores them.

### pilaster (image + workflow silo)

**What it owns:** ComfyUI workflow versions, image generation history, quality scores.
**What Holus calls:**
```python
pilaster.generate_image(brief: str, workflow_id: str) → ImageResult
pilaster.get_best_workflow(style: str) → WorkflowRecommendation
```
**Data stays in:** pilaster's Supabase + Cloudflare R2.

---

## Products Holus Promotes

Defined in `config/products.yaml`. Holus reads this to understand what to promote.

```yaml
products:
  pilaster:
    name: "Pilaster"
    tagline: "The memory layer for ComfyUI"
    audience: "AI artists, ComfyUI users"
    platforms: ["linkedin", "tiktok", "youtube_shorts"]
    content_types: ["tutorial", "before_after", "tips"]

  genpeli:
    name: "Genpeli"
    tagline: "AI video editing pipeline"
    audience: "Content creators, video editors"
    platforms: ["linkedin", "instagram"]
    content_types: ["demo", "tutorial", "case_study"]

  invoz:
    name: "Invoz"
    tagline: "Audio ML API"
    audience: "Developers"
    platforms: ["linkedin", "twitter"]
    content_types: ["technical_post", "demo"]
```

---

## What Lives Where

| Thing | Lives in | Why |
|-------|---------|-----|
| Social media analytics | social-media-automatization | Source of truth — Holus reads, never stores |
| Video files | genpeli / R2 | genpeli owns video creation |
| Image files | pilaster / R2 | pilaster owns image generation |
| Marketing strategy decisions | `.self-improvement/` | Holus owns the strategy layer |
| Product definitions | `config/products.yaml` | Single source for what Holus promotes |
| Content performance patterns | `.self-improvement/MEMORY.md` | Learned by Holus over time |
| Posting queue + accounts | social-media-automatization | Never centralized in Holus |

---

## What Is NOT in Holus

**Trading** — pythia and milo-to-the-moon are completely isolated.
They run their own cron jobs, their own strategies, never communicate with Holus.

**Publishing logic** — social-media-automatization handles posting,
rate limiting, account management, bilingual formatting.
Holus just calls its API.

**Video rendering** — genpeli handles ffmpeg, whisper, caption burning.
Holus calls its API with a brief.

**Image generation** — pilaster handles ComfyUI, Replicate, quality scoring.
Holus calls its API with a brief.

---

## Core (`src/holus/core/`)

Minimal shared infrastructure.

- `config.py` — loads `config/base.yaml` + `config/*.yaml` + env vars. Env vars always win.
- `kill_switch.py` — global pause for when something goes wrong.
- `models.py` — shared Pydantic models: `ContentDecision`, `CampaignResult`, `AnalyticsSnapshot`.

---

## Agents (`src/holus/agents/`)

### marketing/ — the primary agent

The brain. Runs the ReAct loop: observe analytics → reason about strategy → act via MCP tools.
Runs on Opus for strategy decisions, Sonnet for content generation.

### finance/ — simple weekly report (Phase 1.5)

Not LangGraph. A Python script that:
- Reads Stripe for revenue (Pilaster credits sold)
- Reads Anthropic + Replicate usage for costs
- Calculates net P&L
- Sends report to Telegram

### coordinator/ — cross-product synthesis (Phase 3, do not build yet)

When both marketing and finance agents have 2+ months of data,
the coordinator reads both and finds cross-product patterns.
Not needed until then.

---

## Build Order

**Phase 1 (now): One working loop**
- Write `config/products.yaml` describing your products
- Build `social-media-mcp`: `get_analytics()` and `schedule_post()`
- Marketing agent observes analytics, decides, you approve, it posts
- Log every decision to trajectory.jsonl

**Phase 2 (when Phase 1 is working): Automate**
- Cron triggers the agent weekly
- Telegram bot for manual triggers + approval gates
- Agent runs with weekly human review

**Phase 3 (when Phase 2 has 4+ weeks of data): Optimize**
- Pattern analysis on what converts
- Finance agent added
- Coordinator added if cross-product patterns emerge

Do not build Phase 2 before Phase 1 produces content you are proud of.
Do not build Phase 3 before Phase 2 has real performance data.
