# Holus System Memory

Accumulated knowledge from agent operations. Updated by the manager agent after each cycle.

**Last updated:** 2026-03-02
**Updated by:** Builder (cycle 37 — Sprint 2 complete)

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

## Key Files Reference

### Agent Code
| File | Purpose |
|------|---------|
| `src/holus/agents/marketing/agent.py` | Main ReAct loop (observe → reason → act → evaluate) |
| `src/holus/agents/marketing/prompts.py` | Authority-building prompt templates |
| `src/holus/agents/marketing/models.py` | ContentDecision, BrandIdentity, NicheInsight, etc. |
| `src/holus/agents/marketing/repurpose.py` | LinkedIn → 4 platform adaptation |
| `src/holus/agents/marketing/content_queue.py` | Content review queue |
| `src/holus/agents/marketing/review.py` | Human review CLI |

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

## What's Next (Sprint 3 candidates)

**Not yet prioritized. Sprint 3 should focus on:**
1. **First real content cycle** — Run the agent end-to-end with real MCP calls, produce content Camilo approves
2. **MCP server connections** — genpeli MCP (not built), pilaster MCP (not e2e tested), social-media MCP (not e2e tested)
3. **Camilo brand.yaml review** — 6 TODO blocks need his input
4. **Scheduling activation** — launchd plists exist but aren't activated (Spec 013)
5. **Finance agent** — Simple weekly P&L report (Phase 1.5 in ARCHITECTURE.md)

---

## System Incidents

- Health check exit code bug (cycle 19): exited non-zero on degraded status (Redis optional in Phase 1). Fixed.
- Background CLI agent hung for 31+ minutes (cycle 34): killed and implemented directly. Recurring issue.
