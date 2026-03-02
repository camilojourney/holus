# NEXT.md — Holus Task Priority Queue

Last updated: 2026-03-02

## Priority Guide
- **P0** — Blocking. Nothing else works until this is fixed.
- **P1** — Critical path. Required for first real content cycle.
- **P2** — High value. Enables publishing and review flow.
- **P3** — Medium value. Automation and scheduling prep.
- **P4** — Nice to have. Polish, cleanup, future prep.

---

## Spec Status (as of 2026-03-02)

| Spec | Name | Status |
|------|------|--------|
| 001 | Core Infrastructure | Partial (config, kill switch, events, health: done; docker compose, event bus integration: not tested) |
| 009 | Autonomous Build System | Partial (builder agent, run lock, trajectory logging: done; launchd scheduler: not tested) |
| 010 | Marketing Agent | Implemented (ReAct loop, content queue, review CLI, authority prompts, niche research, brand loader: all done) |
| 012 | Knowledge & Learning | Implemented (knowledge base, trajectory, learning loop, knowledge gaps, archive rotation, README index: all done) |
| 013 | Scheduling & Runtime | Partial (launchd plists exist; not tested/activated) |
| 014 | Genpeli Integration | Partial (video_workflow.py + video_queue.py built; genpeli MCP server: not built) |
| 015 | Pilaster Integration | Partial (pilaster MCP connected + image_workflow.py built; end-to-end not tested) |
| 016 | Social Media Integration V2 | Partial (MCP connected + get_analytics/get_top_posts tools added; end-to-end not tested) |
| 017 | Authority Engine Agent Update | Implemented (brand loader, niche research, authority prompts, content repurposing: all 4 SPECs done, 330 tests) |

---

## Sprint 1 Complete (2026-03-01)

All 18 tasks from the infrastructure sprint are done:
- Core infrastructure, marketing agent, knowledge learning: IMPLEMENTED
- Silo integrations (video/image workflows, MCP configs): BUILT
- Knowledge base (voice profile, content frameworks, 9 files): SEEDED
- 247 tests passing, health checks working, launchd plists validated
- See `.self-improvement/reports/builder/` for cycle details

---

## Sprint 2: Authority Engine Build

Strategic shift: from "promote products" to "build authority for AI consulting pipeline."
Source document: `tasks/next.md`

### P0 — Identity Foundation

- [x] [BUILD] Draft `config/brand.yaml` scaffold — Create the file structure with all required sections (story, positioning, offer, target client, products-as-proof, voice, anti-patterns, competitor accounts). Fill in what's known from tasks/next.md. Mark sections needing Camilo's input with `# TODO: Camilo input needed`. This unblocks downstream tasks.
- [x] [BUILD] Reframe `config/products.yaml` — Shift product descriptions from "features to promote" to "proof points for consulting authority." Each product becomes evidence of builder expertise, not the primary pitch.

### P1 — Strategy Knowledge Rewrite

- [x] [BUILD] Rewrite `content-marketing-strategy.md` — Replace generic research questions with authority-building strategy: LinkedIn-primary, 5 content pillars (builder stories, AI implementation frameworks, industry analysis, results/proof, contrarian takes), 5x/week LinkedIn cadence, consulting lead generation focus.
- [x] [BUILD] Rewrite `audience-profiles.md` — Add primary audience: consulting prospects (CTOs, VPs Eng, founders at 50-500 employee companies considering AI transformation, NYC market). Keep product audiences as secondary (brand builders, not pipeline).
- [x] [BUILD] Rewrite `platforms.md` — LinkedIn-first playbook: hook patterns, post formats (text/carousel/document/video), engagement tactics (comments, DMs, community), algorithm signals (dwell time, comments > likes, shares = gold). Other platforms = repurpose, don't create separate.
- [x] [BUILD] Update `growth-engine-vision.md` — Align with consulting goal: authority-building engine, not product promotion engine. Update target results to consulting metrics (inbound DMs, discovery calls, not just views).

### P2 — Niche Research Capability

- [x] [BUILD] Seed `viral-frameworks.md` — New knowledge file. Research LinkedIn AI consulting/builder space. Document 10+ examples of viral posts: hook, structure, proof element, CTA, why it worked. Machine-readable format like content-frameworks.md.
- [x] [BUILD] Design niche research step — Write spec addendum for Spec 010: new observe sub-step that uses web search to find trending AI consulting content on LinkedIn. Define search queries, extraction patterns, output format. Written to `specs/010-marketing-agent.md` as SPEC-006 (SPEC-005 was already taken by Evaluate Stage).
- [x] [BUILD] Define search queries for niche research — Create `.self-improvement/knowledge/current/niche-research-queries.md` with curated search queries for monitoring the AI consulting/builder niche. Categories: competitor posts, trending topics, viral patterns, industry news.

### P3 — Agent Code Updates (Spec 010 v2)

- [x] [BUILD] Write spec 017 — Authority Engine Agent Update. Covers: brand.yaml loading in observe, niche research step, authority framing in reason, content repurposing in act (LinkedIn → Twitter → Instagram → Threads → Facebook). This is the agent code spec for Sprint 2.
- [x] [BUILD] Implement brand.yaml config loader — Add `config/brand.yaml` reading to `src/holus/core/config.py`. Pydantic model for brand identity. Loaded into every marketing agent cycle.
- [x] [BUILD] Update marketing agent prompts — Replace product-promotion framing with authority-building framing in `src/holus/agents/marketing/prompts.py`. Reference brand.yaml, use consulting language, builder mindset.
- [x] [BUILD] Implement content repurposing logic — New module `src/holus/agents/marketing/repurpose.py`. Takes LinkedIn post → adapts for Twitter (condensed), Instagram (visual), Threads (conversational), Facebook (bilingual ES if applicable). Platform-specific formatting.
- [x] [BUILD] Implement niche research step in observe stage — Add web search capability to marketing agent's observe phase. Agent searches for trending content, extracts patterns, stores in knowledge base. Uses Claude tool_use with web_search.

### P4 — Polish & Infrastructure

- [x] [BUILD] Fix `just check` PATH issue — ruff needs `uv run` prefix in justfile. Minor but annoying.
- [x] [REVIEW] End-to-end authority engine test — Run full marketing agent cycle with brand.yaml → research → reason → create content → review queue. Verify content sounds like Camilo, uses authority framing, targets consulting prospects.
- [x] [BUILD] Update `.self-improvement/MEMORY.md` — Refresh system memory with Sprint 2 learnings: what changed strategically, new file locations, updated agent behavior.

---

## Sprint 3: First Real Content Cycle

Goal: Holus generates its first real LinkedIn post, Camilo reviews and approves it, and it gets published.
This sprint closes the loop from "system built" to "system producing real output."

**Key context:**
- Marketing agent uses Claude API (ANTHROPIC_API_KEY) for LLM calls — strategy (Opus) + content generation (Sonnet)
- Publishing uses the local social-media-automatization API (http://localhost:8000) via MCP tools
- Late API client (late.so) exists but is redundant — social-media MCP is the canonical publishing path
- Agent has `just run-marketing` but it has never been run with real API keys
- 6 sections in `config/brand.yaml` need Camilo's input (marked with TODO)
- 330 tests passing, all mocked — no real API calls tested

### P0 — System Runability

- [x] [BUILD] Create `just preflight` command — Validates environment before running: checks ANTHROPIC_API_KEY is set, brand.yaml exists and parses, knowledge files exist, data dirs exist. Print clear pass/fail for each check with fix instructions. No external calls needed.
- [x] [BUILD] Replace Late API publishing path with social-media MCP — The agent's `publish_approved.py` uses Late API (third-party SaaS). Publishing should go through social-media-automatization's local API instead, which is already running and has MCP tools available. Update `publish_approved.py` to call the social-media API at `http://localhost:8000` (or use the MCP `publish` tool). Remove Late API dependency.
- [x] [BUILD] Update spec 017 status to Implemented — Mark all acceptance criteria as done. Update `specs/README.md` status table. This is bookkeeping from Sprint 2 completion.

### P1 — First Content Generation

- [x] [BUILD] Create `just generate` command — Runs ONE marketing agent cycle in generate-only mode (no publishing). Requires ANTHROPIC_API_KEY. Agent executes: observe (load brand, knowledge, niche research) → reason (Opus decides what to write) → act (Sonnet writes LinkedIn post + repurposes) → evaluate (log trajectory). Output goes to `data/content-queue/` for review. This is the first time the agent produces real content.
- [~] [REVIEW] First real agent run — **BLOCKED: ANTHROPIC_API_KEY in `.env` is expired/invalid (401).** Cycle 43 fixed `.env` loading (preflight + generate both read from `.env`), validated 380 tests pass, but actual generation needs a valid key. Camilo must update the key.
- [ ] [BUILD] Prompt tuning based on first run — After reviewing the first real output, adjust prompts in `prompts.py` for better voice match, hook quality, and content depth. This is iterative — may take 2-3 cycles of generate → review → tune.

### P2 — Review & Publishing Pipeline

- [x] [BUILD] Add dry-run mode to publishing — `just publish --dry-run` shows what would be posted (platform, content preview, character count) without actually posting. Safety net before first real publish.
- [ ] [BUILD] End-to-end publish test — Generate content → approve via `just approve-content` → publish via updated publisher → verify post appears on social media. First real published content through the full pipeline.
- [ ] [REVIEW] Camilo reviews brand.yaml TODOs — 6 sections need human input: consulting pivot story, service pricing/deliverables, entry-point service, discovery call link, target verticals, competitor accounts. Schedule a session. Not blocked by other tasks — agent works with current scaffold.

### P3 — Automation & Feedback Loop

- [x] [BUILD] Test launchd scheduling — Fixed 3 plists: added EnvironmentVariables (PATH, HOME), switched `.venv/bin/python` to `/opt/homebrew/bin/uv run python`, added `just validate-plists` and `just schedule-test` commands. All plists validated with `plutil -lint`, health check runs successfully. To activate: `just schedule`. (Cycle 45)
- [x] [BUILD] Add analytics feedback to observe — Added `get_analytics()` and `get_top_posts()` to `SocialMediaClient`. Marketing agent `observe()` now fetches real analytics from social-media API (7-day summary + top 5 posts). Graceful degradation: skips if no API key or API unreachable. 9 new tests (client + agent). 398 total passing. (Cycle 46)
- [x] [BUILD] Create weekly content calendar view — `just calendar` shows content pipeline status: pending review, approved, published, rejected. Reads both content-queue and video-queue. Supports `--weeks N` and `--all` flags. 22 new tests, 420 total. (Cycle 47)

### P4 — Quality & Cleanup

- [x] [BUILD] Reconcile agent analytics path — Removed Late API client package, tests, config, knowledge file, and all references. Social-media MCP is now the sole analytics path. 405 tests passing. (Cycle 48)
- [ ] [REVIEW] Review Sprint 2 module quality — Code review `repurpose.py`, `niche_research` functions in `agent.py`, updated `prompts.py`. Check for: dead code, error handling gaps, missing edge cases. Fix anything found.
- [ ] [BUILD] Add content quality scoring — Before queuing content for review, run a quick quality check: character limits respected, no anti-pattern language detected, hook present, pillar assigned. Reject low-quality content automatically.
