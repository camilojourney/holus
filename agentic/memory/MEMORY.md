# Holus System Memory

Accumulated knowledge from agent operations. Updated by the manager agent after each cycle.

**Last updated:** 2026-03-20
**Updated by:** Builder (cycle 56 — Sprint 4 P0 complete)

---

## What Holus Does

Holus is an **AI content engine** for Juan's personal brand.

**Updated 2026-03-14:**

**Primary goal:** Establish Juan as a thought leader in AI engineering and bilingual tech.
NOT to promote apps. Apps (Pilaster, genpeli, invoz) are proof points — evidence of
expertise. They're chapters in the story, not the pitch.

**Juan's niche:** Bilingual AI engineer for the 600M Spanish/English market Silicon Valley ignores.
Technical depth + market empathy (lived bilingual experience) + shipping real systems.
Almost no one in AI/tech combines all three. That's the moat.

**Primary platform:** LinkedIn (thought leader goal — B2B, senior engineers, tech leads, CTOs).
**Products are proof points**, not the primary pitch:
- Pilaster = "I built an AI image platform with memory — here's what I learned"
- genpeli = "I automated my video editing pipeline — here's the architecture"
- invoz = "I built an audio ML API for non-native speakers — here's the real problem"

**Silos Holus uses:**
- genpeli → video creation (MCP)
- social-media-automatization → posting + analytics (MCP)
- pilaster → image generation (MCP)

**Silos Holus never touches:**
- pythia, milo-to-the-moon (trading — completely isolated)

---

## Target Audience

| Audience | Platform | Content | Priority |
|----------|----------|---------|----------|
| Senior AI engineers, tech leads, CTOs | LinkedIn | AI Engineering + Building in Public | PRIMARY |
| Bilingual tech community (EN/ES) | Instagram, Threads | Bilingual AI content | Secondary |
| AI dev community | X/Twitter | Quick takes, AI commentary | Secondary |

---

## Content Pillars

1. **Building in Public** — Real shipping: code, decisions, failures, wins. LinkedIn primary.
2. **AI Engineering** — How the tech actually works: models, pipelines, agent architectures. LinkedIn + X.
3. **Bilingual AI** — AI for the 600M Spanish/English market. Instagram + Threads primary.
4. **Systems Thinking** — 5 Wealth, IVY LEE, mental models for engineers. LinkedIn.
5. **Contrarian takes** — "Everyone's doing X wrong. Here's why."

---

## Sprint 1 Summary (2026-03-01, cycles 1-19)

**Infrastructure sprint — COMPLETE.** 18/18 tasks done.

What was built:
- Marketing agent core: ReAct loop, content queue, review CLI (Spec 010)
- Knowledge & learning: 9 knowledge files, trajectory logging, archive rotation (Spec 012)
- Silo integrations: video_workflow.py, image_workflow.py, video_queue.py (Specs 014-016)
- Core infrastructure: config, kill switch, events, health, run lock (Spec 001)
- Voice profile captured from 15 published posts
- 7 content frameworks documented in machine-readable format
- 247 tests passing across 15 test files

**Key stats:** ~47 Python files, ~4,800 LOC, 9 knowledge files

---

## Sprint 2 Summary (2026-03-02, cycles 20-37)

**Authority Engine Build — COMPLETE.** 17/17 tasks done.

### Strategic Shift
From "promote products" to "build authority for AI consulting pipeline."
Every content decision now filtered through: "Does this position Camilo as the
go-to AI transition consultant?"

### What Was Built

**Identity Foundation (P0):**
- `config/brand.yaml` — 289-line brand identity scaffold (story, positioning, offer,
  target client, voice, anti-patterns, competitor accounts). 6 TODO blocks for Camilo input.
- `config/products.yaml` — Reframed from features-to-promote to proof-points-for-consulting.
  New fields: `proof_narrative`, `consulting_angle`, `key_stories`, `cross_product_themes`.

**Strategy Knowledge (P1, 4 files rewritten):**
- `content-marketing-strategy.md` — 5 content pillars, LinkedIn-primary, consulting lead metrics
- `audience-profiles.md` — Consulting prospects primary, prospect psychology, conversion funnel
- `platforms.md` — LinkedIn-first playbook, 8 hook patterns, engagement tactics, repurposing guide
- `growth-engine-vision.md` — Aligned with consulting metrics (inbound DMs, discovery calls)

**Niche Research Capability (P2, 3 new files):**
- `viral-frameworks.md` — 12 reverse-engineered viral LinkedIn frameworks
- `niche-research-queries.md` — 24 queries across 4 categories with rotation schedules
- Spec 010 SPEC-006 — Niche research step design (web search → extract → store)

**Agent Code (P3, Spec 017):**
- `config/brand.yaml` loader → `BrandIdentity` Pydantic model with graceful fallback (SPEC-001)
- Niche research in observe → Claude web_search tool, query rotation, daily/weekly cooldowns (SPEC-002)
- Authority prompts → `prompts.py` rewritten for consulting framing, builder mindset (SPEC-003)
- Content repurposing → `repurpose.py` (230 LOC): LinkedIn → Twitter/Instagram/Threads/Facebook
  with Claude Sonnet adaptation + mechanical fallback (SPEC-004)
- `ContentDecision` model extended: `content_pillar`, `hook`, `framework`, `repurpose_notes`

**Polish (P4):**
- `justfile` — all commands use `uv run` prefix (PATH fix)
- E2E test — 4 integration tests validating full authority engine cycle + anti-patterns

### Key Stats
- **330 tests** passing (247 → 330, +83 new tests)
- **~9,800 LOC** source code (4,800 → 9,800)
- **11 knowledge files** (9 → 11)
- **12 marketing modules** in `src/holus/agents/marketing/`
- **1 new spec** (017 — Authority Engine Agent Update)

---

## Sprint 3 Summary (2026-03-02 to 2026-03-20, cycles 38-54)

**First Real Content Cycle — COMPLETE.** 31/31 tasks done (3 blocked, carried forward).

### What Was Built

**System Runability (P0):**
- `just preflight` — validates environment (API key, brand.yaml, knowledge files, data dirs)
- Replaced Late API publishing with social-media MCP — `publish_approved.py` now uses local API
- Spec 017 marked Implemented, specs/README.md updated

**Content Generation (P1):**
- `just generate` — runs ONE marketing agent cycle in generate-only mode
- Idea-injection pipeline (`idea_runner.py`): Opus plans formats, Sonnet generates, Judge evaluates
- Specialist dispatcher (`specialist_dispatch.py`): hook-architect → storyteller → cta-strategist → voice-guardian
- 3-layer prompt loader: optimizer variants > canonical .md > Python fallback
- Thompson Sampling strategy bandit for (product, content_type, platform) optimization

**Review & Publishing (P2):**
- `just publish --dry-run` — shows what would be posted without actually posting
- E2e publish pipeline: 8 integration tests (enqueue → humanize → approve → publish_all)
- Humanization gate (SPEC-032): content must be humanized before approval, edit distance limits
- Brand.yaml review brief prepared at `data/brand-review-brief.md`

**Quality & Automation (P3-P4):**
- Analytics feedback in observe stage — fetches 7-day summary + top 5 posts from social-media API
- `just calendar` — content pipeline status view (pending, approved, published, rejected)
- Content quality scoring (`quality_score.py`, 270 LOC): char limits, anti-patterns, hook quality
- Quality score display in `just review-content --show <id>`
- Removed Late API client and all references — social-media MCP is sole path
- Sprint 2 module quality review — fixed 3 dead code issues

**Visual Content:**
- Animated infographics (SPEC-033): data_viz, poll, insight templates with Playwright rendering
- Carousel builder with PDF rendering
- A/B visual variant generation for text posts (Sonnet designs, Playwright renders)
- Visual spec converter: data_viz_to_spec, insight_to_spec

**Observatory:**
- FastAPI dashboard (localhost:8000) reading trajectory, AGENTS.yaml, content-queue
- Frontend at localhost:3000

**Agent Intelligence (SPEC-030):**
- Agent registry (32 agents in AGENTS.yaml with .md prompts + YAML frontmatter)
- Evaluator routing: domain-specific judges per content type
- Gap detector + prompt evolution pipeline

**LinkedIn Content Pipeline (SPEC-031):**
- Full pipeline: idea → plan → generate → evaluate → queue → humanize → approve → publish
- Constitutional AI revision loop (critique + revise before queueing)
- Topic index for deduplication (prevents repeating recently published topics)

### Key Stats
- **1170 tests** passing (330 → 1170, +840 new tests)
- **~24,000 LOC** source code (9,800 → 24,000)
- **6 new specs** implemented (027-033)
- **Blocked:** First real run (API key expired), prompt tuning, brand.yaml TODOs

---

## Sprint 4 Summary (2026-03-20, cycles 55-56, in progress)

**Content Quality & Pipeline Hardening.**

### What Was Done
- Instagram video_script hashtag fix — platform-aware post-processing (16 tests)
- Judge retry with backoff — transient errors retried once with 2s backoff (13 tests)
- Spec status hygiene — SPEC-032/033 marked Implemented
- Gitignore cleanup — .failed, data/rendered/, data/examples/, .pipeline-state/

### Current Stats
- **1198 tests** collected (1170 → 1198, +28 new tests)
- **~25,000 LOC** source code

---

## Key Files Reference

### Agent Code
| File | Purpose |
|------|---------|
| `src/holus/agents/marketing/agent.py` | Main ReAct loop (observe → reason → act → evaluate) |
| `src/holus/agents/marketing/idea_runner.py` | Idea-injection pipeline (Opus plans, Sonnet generates, Judge evaluates) |
| `src/holus/agents/marketing/specialist_dispatch.py` | Specialist pipeline with platform-aware post-processing |
| `src/holus/agents/marketing/prompts.py` | Authority-building prompt templates |
| `src/holus/agents/marketing/models.py` | ContentDecision, BrandIdentity, NicheInsight, etc. |
| `src/holus/agents/marketing/repurpose.py` | LinkedIn → 4 platform adaptation |
| `src/holus/agents/marketing/content_queue.py` | Content review queue + humanization gate |
| `src/holus/agents/marketing/review.py` | Human review CLI |
| `src/holus/agents/marketing/quality_score.py` | Content quality scoring (anti-patterns, char limits, hooks) |
| `src/holus/agents/marketing/strategy_bandit.py` | Thompson Sampling for content strategy optimization |
| `src/holus/agents/marketing/platform_config.py` | Per-platform judge rubrics, char limits, risk tiers |
| `src/holus/agents/marketing/topic_index.py` | Topic deduplication (prevents repeating recent topics) |
| `src/holus/self_improvement/judge.py` | JudgeAgent with retry logic + domain-specific routing |
| `src/holus/agents/registry.py` | Agent registry (32 agents) + evaluator routing |

### Config
| File | Purpose |
|------|---------|
| `config/brand.yaml` | Brand identity (story, voice, anti-patterns) |
| `config/products.yaml` | Products as consulting proof points |
| `config/base.yaml` | System defaults |
| `config/guardrails.yaml` | Safety limits (NEVER modify without approval) |

### Knowledge
| File | Purpose |
|------|---------|
| `content-marketing-strategy.md` | Authority-building strategy, 5 pillars, cadence |
| `audience-profiles.md` | Prospect psychology, conversion funnel |
| `platforms.md` | LinkedIn-first playbook, hook patterns |
| `viral-frameworks.md` | 12 reverse-engineered viral post frameworks |
| `niche-research-queries.md` | 24 search queries for niche monitoring |
| `growth-engine-vision.md` | North star: authority engine, not content poster |
| `content-frameworks.md` | 7 content structure templates |
| `voice-profile.md` | Camilo's voice from 15 analyzed posts |

---

## Build Patterns Learned

- Codex and Gemini consistently unavailable — always fall back to Claude tools
- `just check` PATH issue FIXED (cycle 35) — all commands now use `uv run` prefix
- Background CLI agents unreliable (timeouts, zsh escaping) — direct Edit/Write is faster
- Health check exit codes matter for launchd: degraded != unhealthy (fixed in cycle 19)
- GenpeliClient and PilasterClient follow identical architecture — maintainable pattern
- Fallback strategy works well: when external systems unavailable, agent degrades gracefully
- Mock `sonnet_model` must be a string, not MagicMock — Pydantic validation catches this
- Variable shadowing across different code sections causes mypy errors (rename, don't reuse)
- Niche research gracefully degrades — never blocks the observe stage even if web search fails
- Content repurposing: Claude Sonnet adaptation produces better results than mechanical transforms,
  but mechanical fallback ensures the feature never fails

---

## Analytics Source

All analytics data lives in **social-media-automatization**.
Holus reads it via MCP — never stores it.

---

## What's Next (Blocked Items)

**Carried from Sprint 3 — all blocked on external input:**
1. **First real agent run** — BLOCKED: ANTHROPIC_API_KEY in .env is expired (401). Camilo must update.
2. **Prompt tuning** — BLOCKED: depends on first real run output for voice/hook calibration.
3. **Brand.yaml completion** — BLOCKED: 6 TODO sections need Camilo session. Review brief at `data/brand-review-brief.md`.

**When unblocked, next priorities:**
4. **MCP e2e testing** — genpeli MCP (not built), pilaster/social-media MCP (not e2e tested with real calls)
5. **Scheduling activation** — launchd plists validated but not activated (Spec 013)
6. **Finance agent** — Simple weekly P&L report (Phase 1.5 in ARCHITECTURE.md)

---

## System Incidents

- Health check exit code bug (cycle 19): exited non-zero on degraded status (Redis optional in Phase 1). Fixed.
- Background CLI agent hung for 31+ minutes (cycle 34): killed and implemented directly. Recurring issue.
