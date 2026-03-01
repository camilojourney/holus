# Holus Architecture

**What Holus is:** An AI marketing strategist agent that promotes the product portfolio.
It decides what content to create, calls specialized silo tools to produce it,
and learns from results to improve strategy over time.

**What Holus is not:** A unified codebase that replaces the individual repos.
Not a trading system. Not a content publisher. Not a video generator.
Those are silos. Holus uses them as tools.

**Last updated:** 2026-02-28
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
    (edit videos)  (post + analytics) (generate images
          │               │            + characters
          ▼               ▼            + short video)
       genpeli      social-media-         │
                    automatization        ▼
                                     pilaster.ai
                                         │
                                    ┌────┼────┐
                                    ▼    ▼    ▼
                                ComfyUI Repl. Runway
                                (swappable backends)
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

### genpeli (video editing silo)

**What it is:** An AI video editing pipeline for human footage. Takes raw video,
removes silences and fillers, burns word-by-word captions, normalizes audio,
and delivers polished shorts. Not a video creator from scratch — a video editor.

**What it owns:** Video processing pipeline, ffmpeg workflows, Whisper transcription.
**What Holus calls:**
```python
genpeli.process_video(video_urls: list[str], instruction: str) → JobResult
genpeli.check_video_status(job_id: str) → JobStatus
genpeli.get_video_preview(job_id: str) → PreviewResult
genpeli.approve_video(job_id: str) → ApprovalResult
genpeli.reject_video(job_id: str, reason: str) → RejectionResult
```
**Data stays in:** genpeli's own storage.

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

### pilaster (image generation platform silo)

**What it is:** An AI image generation platform with memory. Backend-agnostic —
ComfyUI, Replicate, Runway, or any future engine are swappable backends.
Users never see nodes. They pick a character, a template, and generate.

**What it owns:**
- Character registry: LoRAs, reference sheets, metadata for consistent characters
- Generation abstraction: backend-agnostic `generate()` interface
- Templates: reusable generation presets ("product shot", "anime scene", "tutorial frame")
- Experiment memory: every generation tracked with outcomes and quality scores
- Short video: AnimateDiff/SVD clips via ComfyUI backend

**What Holus calls:**
```python
pilaster.generate(character: str, template: str, prompt: str) → ImageResult
pilaster.get_characters() → List[Character]
pilaster.get_templates(style: str) → List[Template]
pilaster.query_experiments(query: str, outcome: str) → List[Experiment]
pilaster.get_successful_prompts(style: str) → List[Prompt]
```
**Data stays in:** pilaster's Supabase + Cloudflare R2.
**Backends are swappable.** The memory, characters, and templates are the product.

---

## Products Holus Promotes

Defined in `config/products.yaml`. Holus reads this to understand what to promote.

```yaml
products:
  pilaster:
    name: "Pilaster"
    tagline: "AI image generation platform with memory"
    audience: "AI artists, content creators, image generation users"
    platforms: ["linkedin", "tiktok", "youtube_shorts"]
    content_types: ["tutorial", "before_after", "tips", "character_showcase"]

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
| Character LoRAs + references | pilaster / Supabase + R2 | pilaster owns visual identity |
| Generation templates | pilaster / Supabase | pilaster owns reusable presets |
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

**Video editing** — genpeli handles ffmpeg, whisper, caption burning.
It edits human footage into polished shorts. Holus sends raw video, genpeli returns edited output.

**Image generation** — pilaster is a generation platform with memory.
It owns character identity (LoRAs, references), templates, and experiment history.
Backends (ComfyUI, Replicate, Runway) are swappable — the memory and characters
are the product. Holus calls its API with a character + template + prompt.

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
- Connect to social-media MCP (already exists in silo repo — add `get_analytics` + `get_top_posts` tools)
- Connect to pilaster MCP (already exists — add `get_templates` + `get_successful_prompts` tools)
- Build genpeli MCP server in genpeli repo (wraps existing REST API)
- Marketing agent observes analytics, decides, you approve, it posts
- Log every decision to trajectory.jsonl

**Phase 2 (when Phase 1 is working): Automate**
- launchd triggers the agent every 30 minutes
- Telegram bot for manual triggers + approval gates
- Agent runs with weekly human review

**Phase 3 (when Phase 2 has 4+ weeks of data): Optimize**
- Pattern analysis on what converts
- Finance agent added
- Coordinator added if cross-product patterns emerge

Do not build Phase 2 before Phase 1 produces content you are proud of.
Do not build Phase 3 before Phase 2 has real performance data.
