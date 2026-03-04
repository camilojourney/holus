# Holus System Memory

Accumulated knowledge from agent operations. Updated by the manager agent after each cycle.

**Last updated:** 2026-03-04
**Updated by:** Builder (cycle 74 — Sprint 4 review)

---

## What Holus Does

Holus is an **AI authority-building engine** for Camilo's consulting pipeline.
It builds Camilo's reputation as the go-to AI transition consultant by creating
content that demonstrates builder expertise, targets consulting prospects,
and drives inbound leads.

**Primary goal:** Position Camilo for NYC AI consulting launch (2-month horizon).
**Primary platform:** LinkedIn (everything else is repurposed from LinkedIn).
**Products are proof points**, not the primary pitch:
- Pilaster = "I built an AI image platform with memory"
- genpeli = "I automated my video editing pipeline"
- invoz = "I built an audio ML API"

**Silos Holus uses:**
- genpeli → video creation (MCP)
- social-media-automatization → posting + analytics (MCP)
- pilaster → image generation (MCP)

**Silos Holus never touches:**
- pythia, milo-to-the-moon (trading — completely isolated)

---

## Target Audience

| Audience | Role | Where | Priority |
|----------|------|-------|----------|
| Consulting prospects | CTOs, VPs Eng, founders (50-500 employees) | LinkedIn | PRIMARY |
| Pilaster users | ComfyUI artists, AI image creators | TikTok, LinkedIn | Secondary |
| genpeli users | Content creators, video editors | LinkedIn, Instagram | Secondary |
| invoz users | Developers | LinkedIn, Twitter | Secondary |

---

## Content Pillars (Authority Framework)

1. **Builder stories** — "I built X, here's what I learned"
2. **AI implementation frameworks** — "How to actually deploy AI in your company"
3. **Industry analysis** — "What's working in AI right now and what's hype"
4. **Results/proof** — Real numbers, real architectures, real outcomes
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

## Sprint 3 Summary (2026-03-03, cycles 38-53)

**First Real Content Cycle — PARTIAL.** 16/18 tasks done, 2 blocked on expired ANTHROPIC_API_KEY.

What was built:
- `just preflight` — environment validation before running
- Publishing path switched from Late API to social-media MCP
- `just generate` — runs one marketing agent cycle in generate-only mode
- Dry-run publishing mode (`just publish --dry-run`)
- E2E publish pipeline tests (15 tests across 5 classes)
- Analytics feedback loop in observe stage
- Weekly content calendar view (`just calendar`)
- Content quality scoring with auto-reject below score 60
- Quality score display in review CLI
- Late API fully removed — social-media MCP is sole path
- launchd scheduling tested and validated

**Blocked:** First real agent run + prompt tuning (ANTHROPIC_API_KEY expired)
**Key stats:** 475 tests, ~10K LOC

---

## Sprint 4 Summary (2026-03-03—04, cycles 54-74)

**Test Coverage & Refactoring — COMPLETE.** 19/19 tasks done.

### Refactoring
- `agent.py` refactored: 1,101 → 665 LOC (−40%)
- Extracted 3 new modules: `niche_research.py` (314 LOC), `content_generation.py` (136 LOC), `json_parsing.py` (181 LOC)
- Source modules reduced from 53 to 41 (consolidated duplicates during refactor)

### Test Coverage
- **860 tests** (475 → 860, +385 new tests)
- **Module coverage: 32% → 78%** (target was 60%+, exceeded)
- 32/41 modules have dedicated tests
- 9 untested: `__main__.py` (entry point), 4 stub agents (coding, content, coordinator, pilaster), `review_videos.py`, `process_manager.py`, `mem0_client.py`, `langfuse_client.py`

### New test files added (Sprint 4)
| Module | Tests | Cycle |
|--------|-------|-------|
| niche_research.py | 43 | 63 |
| content_generation.py | 26 | 64 |
| json_parsing.py | 66 | 65 |
| prompts.py | 55 | 66 |
| content_queue.py | 31 | 67 |
| claude_api/client.py | 38 | 68 |
| core/events.py | 14 | 69 |
| agents/base.py | 32 | 70 |
| self_improvement/judge.py | 27 | 71 |
| self_improvement/reflexion.py | 34 | 72 |
| self_improvement/prompt_optimizer.py | 33 | 73 |

### Bug found & fixed
- `prompt_optimizer.py`: `OPTIMIZER_PROMPT` had unescaped `{}` in JSON example template — caused KeyError at runtime. Fixed in cycle 73.

**Key stats:** 860 tests, 10,941 source LOC, 13,970 test LOC, 34 test files

---

## Key Files Reference

### Agent Code
| File | Purpose |
|------|---------|
| `src/holus/agents/marketing/agent.py` | Main ReAct loop (665 LOC, refactored from 1,101) |
| `src/holus/agents/marketing/niche_research.py` | NicheResearcher class (extracted from agent.py) |
| `src/holus/agents/marketing/content_generation.py` | Text generation helpers (extracted from agent.py) |
| `src/holus/agents/marketing/json_parsing.py` | JSON parsing utilities (extracted from agent.py) |
| `src/holus/agents/marketing/prompts.py` | Authority-building prompt templates |
| `src/holus/agents/marketing/models.py` | ContentDecision, BrandIdentity, NicheInsight, etc. |
| `src/holus/agents/marketing/repurpose.py` | LinkedIn → 4 platform adaptation |
| `src/holus/agents/marketing/content_queue.py` | Content review queue |
| `src/holus/agents/marketing/quality_score.py` | Content quality scoring (auto-reject < 60) |
| `src/holus/agents/marketing/review.py` | Human review CLI |
| `src/holus/agents/marketing/publish_approved.py` | Publishing via social-media MCP |

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

## What's Next (Sprint 5 candidates)

**Not yet prioritized. Sprint 5 should focus on:**
1. **First real content cycle** — BLOCKED on ANTHROPIC_API_KEY (expired since Sprint 3). Camilo must update.
2. **Prompt tuning** — Depends on first real run output.
3. **`just coverage` command** — Run pytest with coverage report for per-module percentages.
4. **MCP server e2e testing** — genpeli MCP (not built), pilaster MCP (not tested), social-media MCP (not tested)
5. **Camilo brand.yaml review** — 6 TODO blocks need his input
6. **Scheduling activation** — launchd plists tested, not yet activated

---

## System Incidents

- Health check exit code bug (cycle 19): exited non-zero on degraded status (Redis optional in Phase 1). Fixed.
- Background CLI agent hung for 31+ minutes (cycle 34): killed and implemented directly. Recurring issue.
