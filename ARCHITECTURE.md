# Holus Architecture

**What Holus is:** A thought-to-content studio for the product portfolio.
It ingests one thought from a person or online source, transforms it into useful
platform-native formats, creates text/image/carousel assets, reviews them, posts
or schedules through Holus Social API, and learns from results.

**What Holus is not:** A unified codebase that replaces the individual repos.
Not a trading system. Not an account owner. Not a silent publisher. Not a video
generator for the current build. Holus Social API owns posting and analytics;
Genpeli/video is deferred as a live integration. The public Holus demo uses a
local adapter only: the browser never calls Genpeli or opens a localhost event
stream on a public or demo surface.

**Last updated:** 2026-08-14
**Update cadence:** Only on major structural changes.

---

## Mental Model

```
                        HOLUS
                   (Thought Studio)
                          |
  thought source -> normalize -> content set -> variants -> visuals -> review
                          |
                          ▼
                  Holus Social API
              (schedule/post + analytics)
                          |
                          ▼
                  social platforms

  Public generation demo:
    local Holus adapter -> bounded lifecycle

  Future authenticated seam:
    Holus BFF -> mapped Genpeli job
```

Holus holds the BRAIN and studio state: source metadata, decisions, generated
variants, visual assets, review state, and learning.
Holus Social API holds the publishing HANDS: accounts, posting queue, platform
analytics, and performance snapshots.

Data never flows back into Holus permanently.
Holus reads silo data to make decisions, but the source of truth stays in the silo.

### Public generation boundary

Holus owns the public product experience at
`https://holus.camilomartinez.co` and its future authenticated BFF. Genpeli is
a private generation capability, not a public application or browser
integration. The only planned cross-service seam is a Holus BFF that can create
one mapped Genpeli job, read that mapped job's restricted status, and proxy its
preview. The browser does not contact Genpeli.

The versioned `holus.generation.v1` contract is implemented in
`src/holus/generation/` and
`observatory/frontend/src/lib/generation/`. It permits only a constrained create
request, a mapped job status, and a preview reference. It deliberately excludes
costs, raw traces, artifacts or artifact URLs, review, rejection, delivery,
publishing, credentials, and operator controls. Until an authenticated BFF is
connected, the local adapter is visibly labelled as demo data or connection
required and never creates a live job.

Public Observatory pages also do not claim unavailable real-time telemetry:
live events require an authenticated backend connection and public/demo mode
does not open localhost SSE. This behavior is owned by
`observatory/frontend/src/lib/connection.ts`.

---

## Agent Intelligence & Self-Improvement

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                    SELF-IMPROVEMENT LOOP                            │
 │                                                                     │
 │ agentic/agents/AGENTS.yaml ─ AgentRegistry ─ PromptLoader (3 layers)│
 │       │                      │                    │                 │
 │       │            get_evaluator_for()    Layer 1: config/prompts/  │
 │       ▼                      │      Layer 2: agentic/agents/*.md    │
 │  32 agent prompts            ▼           Layer 3: Python fallback   │
 │  (.md + YAML frontmatter)  JudgeAgent                               │
 │                     evaluate_with_routing()                         │
 │                              │                                      │
 │                    ┌─────────┼──────────┐                           │
 │                    ▼         ▼          ▼                           │
 │            written-content  visual   brand-safety                   │
 │            -judge          -judge    -judge                         │
 │            (7 domain-expert evaluators)                              │
 │                    │                                                │
 │                    ▼                                                │
 │            trajectory.jsonl ──→ WeeklyLearningLoop                  │
 │                                        │                           │
 │                              ┌─────────┼──────────┐                │
 │                              ▼         ▼          ▼               │
 │                         MEMORY.md  lessons.json  knowledge/        │
 │                                                                     │
 │  Observatory (localhost:8000 API + localhost:3000 dashboard)         │
 │    reads trajectory, AGENTS.yaml, eval_history, content-queue       │
 └──────────────────────────────────────────────────────────────────────┘
```

**Three-layer prompt resolution:** When an agent loads its system prompt, PromptLoader
checks (1) optimizer-promoted variant in `config/prompts/`, (2) canonical `.md` file in
`agentic/agents/`, (3) hardcoded Python constant. First hit wins. This enables A/B testing and
prompt optimization without changing code.

**Evaluator routing:** The judge dispatches evaluation to domain-specific evaluators
based on content type. A LinkedIn text post goes to `written-content-judge` +
`brand-safety-judge`. A carousel goes to `visual-content-judge` + `brand-safety-judge`.
Each evaluator has its own rubric dimensions (not generic correctness/completeness).

---

## The Thought Studio Loop

Holus runs as a thought-to-content pipeline through the API, CLI, or future agent cycles.

```
INGEST
  -> accept thought text or URL at /api/v1/content/from-thought
  -> store source_type, source_url, and raw source metadata
  -> optionally accept scored Research Radar candidates after human approval

NORMALIZE
  -> extract useful text from the source
  -> create one Thought with traceable lineage

PLAN
  -> choose PlatformActivation rows such as linkedin_text, instagram_image,
     linkedin_carousel, threads_text, twitter_x_thread
  -> build source context, a strategic brief, a primary-channel recommendation,
     and per-channel transformation jobs

GENERATE
  -> create ContentVariant rows for each platform
  -> render VisualAsset files into data/rendered-content for image/carousel outputs

REVIEW
  -> preserve platform-fit evidence and an explicit approval checklist
  -> run judges and preserve human review as the default gate
  -> PATCH review state locally; reserve an outbox intent before explicit dispatch
  -> append privacy-safe lineage events to data/lineage/events.jsonl

PUBLISH OR SCHEDULE
  -> explicit endpoint calls HolusSocialAPIClient with platforms payload
  -> dry-run returns the payload without posting

LEARN
  -> read PerformanceSnapshot data from Holus Social API
  -> update trajectory, memory, lessons, and next cycle planning
```

---

## Silo Architecture

Each silo is an independent repo that owns its own data and execution.
Holus communicates with silos via MCP (Model Context Protocol) tool calls.

### Holus Social API (publishing + analytics boundary)

**What it owns:** Social accounts, posting queue, scheduling, platform analytics,
top posts, and performance snapshots.
**What Holus calls:**
```python
holus_social.publish(content, platforms, media_url, media_type) -> PublishResult
holus_social.schedule_post(content, platforms, scheduled_at) -> ScheduleResult
holus_social.get_analytics(days: int, platform: str) -> AnalyticsReport
holus_social.get_top_posts(limit: int, metric: str) -> list[Post]
```
**Data stays in:** Holus Social API storage. Holus records references and snapshots
only when needed for learning.

Legacy environment aliases remain supported:
`SOCIAL_MEDIA_API_BASE_URL` -> `HOLUS_SOCIAL_API_BASE_URL`,
`POSTING_API_KEY` -> `HOLUS_SOCIAL_API_KEY`.

### Genpeli (private future video capability)

**What it is:** An AI video editing pipeline for human footage. Takes raw video,
removes silences and fillers, burns word-by-word captions, normalizes audio,
and delivers polished shorts. Not a video creator from scratch — a video editor.

**What it owns:** Video processing pipeline, ffmpeg workflows, Whisper transcription.
**Holus integration:** Deferred. If connected, an authenticated Holus BFF - not
the browser - will use the public-generation boundary above to create a mapped
job, read its restricted status, and proxy its preview. Approval, rejection,
delivery, artifacts, and operator controls are not public BFF contract fields.
**Data stays in:** Genpeli's own storage. This integration remains deferred
until the text/image/carousel workflow is solid.

### Pilaster (future optional AI-image adapter)

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
pilaster.generate_image(backend: str, recipe: StructuredRecipe) → ImageResult
pilaster.get_characters() → List[Character]
pilaster.get_templates(style: str) → List[Template]
pilaster.query_experiments(query: str, outcome: str) → List[Experiment]
pilaster.get_successful_prompts(style: str) → List[Prompt]
```

**Structured prompt recipes:** Holus never sends flat prompt strings to Pilaster.
Instead, it sends a structured recipe that decomposes image intent into independent
dimensions: `subject`, `style`, `composition`, `lighting`, `quality`, `negative`.
This maps to ComfyUI nodes but works identically across all prompt-based backends
(DALL-E 3, Imagen 3, Fal.ai, Gemini). Pilaster assembles the recipe into whatever
format the backend needs. See [Spec 015](specs/015-pilaster-integration.md) for the
full recipe format and examples.

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
| Thought source metadata | `data/content-queue/*.yaml` | Each generated item keeps source_type/source_url/source_raw_input |
| Research digests and candidates | `data/research/` | Radar outputs remain reviewable before entering the Thought Studio |
| Rendered image/carousel files | `data/rendered-content` | Holus visual engine owns current PNG/PDF outputs |
| Social media analytics | Holus Social API | Source of truth; Holus reads, never stores permanently |
| Future video files | genpeli / R2 | Genpeli owns future video creation |
| Future AI image files | pilaster / R2 | Pilaster can become an optional AI-image adapter |
| Character LoRAs + references | pilaster / Supabase + R2 | pilaster owns visual identity |
| Generation templates | pilaster / Supabase | pilaster owns reusable presets |
| Marketing strategy decisions | `.self-improvement/` | Holus owns the strategy layer |
| Product definitions | `config/products.yaml` | Single source for what Holus promotes |
| Content performance patterns | `agentic/memory/MEMORY.md` | Learned by Holus over time |
| Posting queue + accounts | Holus Social API | Never centralized in Holus |
| Agent definitions | `agentic/agents/AGENTS.yaml` + `agentic/agents/**/*.md` | Single registry for all agents |
| Judge evaluations | `trajectory.jsonl` metadata | Per-piece quality scores from domain evaluators |
| Observatory data | FastAPI reads from all above files | No new DB — reads JSONL/YAML/MD directly |
| Provenance manifest | `data/lineage/events.jsonl` | Holus-owned, append-only, privacy-safe read boundary; see [lineage contract](docs/lineage.md) |

---

## What Is NOT in Holus

**Trading** — pythia and milo-to-the-moon are completely isolated.
They run their own cron jobs, their own strategies, never communicate with Holus.

**Publishing logic** — Holus Social API handles posting, scheduling,
rate limiting, account management, bilingual formatting, and analytics.
Holus prepares reviewed payloads and calls its API explicitly.

**Video editing** — Genpeli is deferred. It can later handle ffmpeg,
whisper, caption burning, and polished shorts, but the current build should
not block on video.

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

The brain and studio. Runs the Thought Studio loop: ingest source thought,
normalize, plan content set, generate variants, render visuals, review,
schedule/publish through Holus Social API, then learn from performance.

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
- Make `/api/v1/content/from-thought` the primary intake
- Generate text, image, and carousel variants from one thought
- Render PNG/PDF assets with the Holus visual engine
- Keep review and dispatch explicit; persist the outbox intent locally before any
  schedule or publish request reaches Holus Social API
- Rename and wire Holus Social API with legacy env aliases
- Log every decision to trajectory.jsonl

**Phase 2 (when Phase 1 is working): Automate**
- launchd triggers the agent every 30 minutes
- Telegram bot for manual triggers + approval gates
- Agent runs with weekly human review
- Optional Pilaster AI-image adapter if local visual quality is not enough
- Optional Genpeli video adapter after text/image/carousel is excellent

**Phase 3 (when Phase 2 has 4+ weeks of data): Optimize**
- Pattern analysis on what converts
- Finance agent added
- Coordinator added if cross-product patterns emerge

Do not build Phase 2 before Phase 1 produces content you are proud of.
Do not build Phase 3 before Phase 2 has real performance data.
