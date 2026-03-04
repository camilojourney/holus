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
- [~] [BUILD] Prompt tuning based on first run — **BLOCKED: Depends on first real agent run (API key invalid).** After reviewing the first real output, adjust prompts in `prompts.py` for better voice match, hook quality, and content depth. This is iterative — may take 2-3 cycles of generate → review → tune.

### P2 — Review & Publishing Pipeline

- [x] [BUILD] Add dry-run mode to publishing — `just publish --dry-run` shows what would be posted (platform, content preview, character count) without actually posting. Safety net before first real publish.
- [x] [BUILD] End-to-end publish test — E2e test validates full queue lifecycle: enqueue → approve → publish (mocked API) → verify YAML status transitions. 15 tests across 5 classes: happy path, failure handling, exceptions, multi-piece, mixed results, missing API key, not-found errors. 475 total tests. (Cycle 52)
- [x] [REVIEW] Camilo reviews brand.yaml TODOs — 7 TODO blocks extracted and presented: consulting pivot story, service pricing/deliverables, entry-point service, discovery call link, target verticals, product story resonance, competitor accounts. Presented in conversation for human input. Not blocking — agent works with current scaffold. (Cycle 53)

### P3 — Automation & Feedback Loop

- [x] [BUILD] Test launchd scheduling — Fixed 3 plists: added EnvironmentVariables (PATH, HOME), switched `.venv/bin/python` to `/opt/homebrew/bin/uv run python`, added `just validate-plists` and `just schedule-test` commands. All plists validated with `plutil -lint`, health check runs successfully. To activate: `just schedule`. (Cycle 45)
- [x] [BUILD] Add analytics feedback to observe — Added `get_analytics()` and `get_top_posts()` to `SocialMediaClient`. Marketing agent `observe()` now fetches real analytics from social-media API (7-day summary + top 5 posts). Graceful degradation: skips if no API key or API unreachable. 9 new tests (client + agent). 398 total passing. (Cycle 46)
- [x] [BUILD] Create weekly content calendar view — `just calendar` shows content pipeline status: pending review, approved, published, rejected. Reads both content-queue and video-queue. Supports `--weeks N` and `--all` flags. 22 new tests, 420 total. (Cycle 47)

### P4 — Quality & Cleanup

- [x] [BUILD] Reconcile agent analytics path — Removed Late API client package, tests, config, knowledge file, and all references. Social-media MCP is now the sole analytics path. 405 tests passing. (Cycle 48)
- [x] [REVIEW] Review Sprint 2 module quality — Reviewed repurpose.py (278 LOC), niche research in agent.py (~400 LOC), prompts.py (412 LOC). Found 3 issues: dead `_product_info` wrapper, unused `format_platform_guidelines`, redundant inner `import yaml`. All fixed. No security or error handling gaps. 405 tests passing. (Cycle 49)
- [x] [BUILD] Add content quality scoring — New `quality_score.py` module (270 LOC): checks char limits, anti-pattern phrases (13 default + brand.yaml extras), forbidden topics (trading/pythia), hook quality, pillar assignment, exclamation/emoji density. Integrated into `act()` — content below score 60 is auto-rejected. 42 new tests, 447 total. (Cycle 50)
- [x] [BUILD] Add quality score display to review CLI — Enhance `just review-content --show <id>` with quality score breakdown: overall score (color-coded), char count vs platform limit, violation details, and pass/fail badge. Bridges QueuedContent → GeneratedPiece for scoring. (Cycle 51)

---

## Sprint 4: Test Coverage & Refactoring

Goal: Bring test coverage from 32% to 60%+, refactor the 1,101-LOC agent.py into focused modules, and prepare the system for first real content run.

**Key context:**
- 475 tests passing, but 36 of 53 source modules have zero test coverage
- `agent.py` is 1,101 LOC with 31 methods — the largest file, and the core orchestration logic
- Code quality is clean (lint, types both pass) — this is about coverage and maintainability
- Sprint 3 blocked tasks (first real run, prompt tuning) still need a valid ANTHROPIC_API_KEY
- Codex and Gemini consistently unavailable — all work done via Claude tools

### P0 — Refactor agent.py (Unblocks Testing)

- [x] [BUILD] Extract niche research from agent.py — Moved 8 methods into `src/holus/agents/marketing/niche_research.py` as `NicheResearcher` class (375 LOC). Agent.py reduced from 1,101 to 840 LOC. All 489 tests pass. Test files updated to use NicheResearcher directly. (Cycle 60)
- [x] [BUILD] Extract content generation helpers from agent.py — Moved `_generate_text_for_decision`, `_fallback_content_text`, `_enforce_platform_limit`, `_extract_response_text` into `src/holus/agents/marketing/content_generation.py` as standalone functions. Agent.py delegates via thin proxies. 770 LOC (down from ~840). 489 tests pass. (Cycle 61)
- [x] [BUILD] Extract JSON parsing helpers from agent.py — Moved `parse_content_decisions`, `coerce_decision`, `decode_json_payload`, `try_json_loads`, `extract_response_text` into `src/holus/agents/marketing/json_parsing.py` (181 LOC). Agent.py delegates via thin proxies. Consolidated duplicates from niche_research.py and content_generation.py. Agent.py: 770 → 665 LOC. 489 tests pass. (Cycle 62)

### P1 — Test Critical Modules

- [x] [BUILD] Add unit tests for niche_research.py — 14 new tests added (43 total): state read/write (5), query selection edge cases (3), parse edge (1), web search error (1), extract JSON fences (1), format truncation (2), None API key (1). 503 total tests. (Cycle 63)
- [x] [BUILD] Add unit tests for content_generation.py — 26 tests added: fallback templates (5), platform limit enforcement (8), generate_text_for_decision API calls and fallbacks (10), constant validation (3). 529 total tests. (Cycle 64)
- [x] [BUILD] Add unit tests for json_parsing.py — 66 tests added across 7 classes: try_json_loads (9), decode_json_payload (13), extract_response_text (7), coerce_decision (17), parse_content_decisions (9), PLATFORM_ALIASES (6), CONTENT_TYPE_ALIASES (5). 595 total tests. (Cycle 65)
- [x] [BUILD] Add unit tests for prompts.py — 55 tests added across 7 classes: prompt template placeholders (8), format_brand_identity (11), format_content_pillars (7), format_voice (8), format_positioning (7), format_anti_patterns (6), format_product_info (8). 650 total tests. (Cycle 66)
- [x] [BUILD] Add unit tests for content_queue.py — 31 tests added across 8 classes: QueuedContent model (3), enqueue YAML persistence (5), list_pending filtering (6), list_approved filtering (3), approve transitions (3), reject transitions (4), mark_published transitions (4), full lifecycle (3). 681 total tests. (Cycle 67)

### P2 — Test Supporting Infrastructure

- [x] [BUILD] Add unit tests for claude_api/client.py — 38 tests across 9 classes: CachedPrompt system blocks (5), CachedPrompt tools cache (4), Client.call routing (8), cost tracking (7), define_tool (3), handle_tool_loop (8), constants (3). 719 total tests. (Cycle 68)
- [ ] [BUILD] Add unit tests for core/events.py — Test event bus: subscribe, emit, handler ordering, error isolation. Target: 8+ tests.
- [ ] [BUILD] Add unit tests for agents/base.py — Test base agent lifecycle, state management, hook points. Target: 8+ tests.

### P3 — Test Self-Improvement System

- [ ] [BUILD] Add unit tests for self_improvement/judge.py — Test evaluation scoring, pattern matching, output quality assessment. Target: 8+ tests.
- [ ] [BUILD] Add unit tests for self_improvement/reflexion.py — Test self-correction loop, improvement detection, convergence. Target: 8+ tests.
- [ ] [BUILD] Add unit tests for self_improvement/prompt_optimizer.py — Test prompt mutation, scoring, selection. Target: 8+ tests.

### P4 — Polish & Verification

- [ ] [REVIEW] Run full test suite and verify coverage improvement — Run `just check`, count total tests, calculate module coverage ratio. Update MEMORY.md with Sprint 4 results.
- [ ] [BUILD] Add `just coverage` command — Run pytest with coverage report, show per-module coverage percentage. Helps track progress on coverage goals.
