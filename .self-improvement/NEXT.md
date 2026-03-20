# NEXT.md — Holus Task Priority Queue

Last updated: 2026-03-20

## Priority Guide
- **P0** — Blocking. Nothing else works until this is fixed.
- **P1** — Critical path. Required for first real content cycle.
- **P2** — High value. Enables publishing and review flow.
- **P3** — Medium value. Automation and scheduling prep.
- **P4** — Nice to have. Polish, cleanup, future prep.

---

## Spec Status (as of 2026-03-20)

| Spec | Name | Status |
|------|------|--------|
| 001 | Core Infrastructure | Partial (config, kill switch, events, health: done; docker compose, event bus integration: not tested) |
| 009 | Autonomous Build System | Partial (builder agent, run lock, trajectory logging: done; launchd scheduler: tested but not activated) |
| 010 | Marketing Agent | Implemented |
| 012 | Knowledge & Learning | Implemented |
| 013 | Scheduling & Runtime | Partial (plists fixed + validated; not activated) |
| 014 | Genpeli Integration | Partial (video_workflow.py + video_queue.py built; genpeli MCP server: not built) |
| 015 | Pilaster Integration | Partial (pilaster MCP connected + image_workflow.py built; end-to-end not tested) |
| 016 | Social Media Integration V2 | Partial (MCP connected + get_analytics/get_top_posts added; e2e publish tests passing with mocks) |
| 017 | Authority Engine Agent Update | Implemented |
| 027 | Resilient Agent Loop | Implemented |
| 028 | Observatory API | Implemented |
| 029 | Observatory Frontend | Partial |
| 030 | Agent Registry & Self-Improvement | Implemented |
| 031 | LinkedIn Content Pipeline | Implemented |
| 032 | Humanization Gate | Implemented |
| 033 | Animated Infographics | Implemented |

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
- [x] [BUILD] End-to-end publish test — 8 integration tests covering full manual pipeline: enqueue → humanize (SPEC-032 gate) → approve → publish_all (mocked social-media API) → verify status=published. Also tests: humanization enforcement, edit distance limits, multi-piece flows, API failure handling, media attachments, missing API key. (Cycle 52)
- [x] [REVIEW] Camilo reviews brand.yaml TODOs — 6 sections need human input: consulting pivot story, service pricing/deliverables, entry-point service, discovery call link, target verticals, competitor accounts. **Review brief prepared:** `data/brand-review-brief.md` — structured questionnaire for Camilo to fill out. Agent works with current scaffold. (Cycle 54)

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

## Sprint 4: Content Quality & Pipeline Hardening

Goal: Fix recurring content quality issues identified from trajectory data, harden the judge pipeline,
and clean up accumulated tech debt. The content pipeline (idea-runner) is producing content — now make it reliable.

**Key context:**
- 1170 tests passing, ~50+ pipeline runs logged in trajectory
- Instagram video_script format consistently scores PARTIAL (missing hashtag_strategy)
- Judge failures on timeout/invalid JSON produce FAIL with score 0.0, no retry
- SPEC-032 (Humanization Gate) and SPEC-033 (Animated Infographics) were implemented but specs/README.md not updated
- .failed file contains 233 lines of junk data (`{"key": "val"}`)
- data/rendered/, data/examples/, .pipeline-state/ are untracked and should be gitignored
- MEMORY.md last updated 2026-03-02 — needs Sprint 3 summary
- Sprint 3 blocked items carry forward: API key (first real run), prompt tuning, brand.yaml review

### P0 — Content Quality Fixes

- [x] [BUILD] Fix Instagram video_script missing hashtags — Added `_enrich_for_platform()` to `specialist_dispatch.py` and `_get_format_instructions()` to `idea_runner.py`. Both content generation paths now append hashtag blocks + caption instructions for Instagram/TikTok/Facebook video_scripts. LinkedIn unchanged. 16 new tests. (Cycle 56)
- [x] [BUILD] Add judge retry with backoff — Refactored `judge.py`: `evaluate()` now retries on transient errors (timeout, connection, invalid JSON) with exponential backoff (2s base, max 2 attempts). Non-transient errors fail immediately. HTTP 5xx treated as transient. 13 new tests. (Cycle 56)

### P1 — Spec & Status Hygiene

- [x] [BUILD] Update specs/README.md statuses — Marked SPEC-033 as Implemented (was "Not Started" but fully built per git log). Updated Spec Status table in NEXT.md with all 16 specs including 027-033. (Cycle 55)
- [x] [BUILD] Clean .failed file — Runtime health-check artifact (233 lines of `{"key": "val"}`). Added `.failed` to .gitignore. (Cycle 55)
- [x] [BUILD] Add untracked data dirs to .gitignore — Added `data/rendered/`, `data/examples/`, `.pipeline-state/`, `.failed` to .gitignore. (Cycle 55)

### P2 — System Memory

- [x] [BUILD] Update MEMORY.md with Sprint 3 summary — Added Sprint 3 + Sprint 4 summaries, updated key files reference (14 modules), updated "What's Next" with blocked items, stats: 1198 tests, ~25,000 LOC. (Cycle 56)
- [x] [BUILD] Update sprint-state.json — Set cycle=56, added sprint=4 and sprint_name. (Cycle 56)

### P3 — Carry-Forward (Blocked)

- [~] [REVIEW] First real agent run — **BLOCKED: ANTHROPIC_API_KEY needed.** Carried from Sprint 3.
- [~] [BUILD] Prompt tuning based on first run — **BLOCKED: Depends on first real run.** Carried from Sprint 3.
- [~] [REVIEW] Brand.yaml completion — **BLOCKED: Needs Camilo session.** Review brief at `data/brand-review-brief.md`. Carried from Sprint 3.

---

## Sprint 5: Config Consolidation & Test Coverage

Goal: Eliminate the PROXY_URL duplication across 8 files, add test coverage for critical untested modules
(MCP clients, API routes), and improve content quality for underperforming platforms.

**Key context:**
- PROXY_URL (`http://localhost:8080/v1/chat/completions`) duplicated in 8 files — config.py already has `anthropic_base_url`
- PROXY_HEADERS (`Authorization: Bearer local`) duplicated in 5 files alongside PROXY_URL
- 37 source files have zero test coverage — critical gaps in MCP clients, API routes, core agents
- Trajectory pass rate: 60.7% (17/28). Instagram caption: 20%, video_script: 25%
- Threads content scored low on `native_feel` — agent produces LinkedIn "broetry" style on Threads
- Prompt adherence: agent rewrites provided hooks instead of using them (Twitter thread scored 0.82)
- Sprint 4 fixed hashtags + judge retry — those issues should not recur in new trajectory entries
- 3 blocked items carry forward (API key, prompt tuning, brand.yaml)

### P0 — PROXY_URL Consolidation

- [x] [BUILD] Create shared LLM proxy helper — New module `src/holus/core/llm_proxy.py` with `get_proxy_url()`, `get_proxy_headers()`, `get_proxy_api_base()`, `get_proxy_api_key()`. Reads `ANTHROPIC_BASE_URL` + `LLM_PROXY_AUTH_TOKEN` env vars. Also provides module-level `PROXY_URL`/`PROXY_HEADERS` constants. 11 tests. (Cycle 58)
- [x] [BUILD] Replace PROXY_URL in marketing modules — Updated `idea_runner.py`, `quality_compounding.py`, `revision_loop.py`, `platform_adapter.py` to import from `core.llm_proxy`. `specialist_dispatch.py` had no PROXY_URL to replace. (Cycle 59)
- [x] [BUILD] Replace PROXY_URL in infrastructure modules — Updated `core/resilience.py`, `self_improvement/judge.py`, `self_improvement/dspy_optimizer.py`, and `specialist_dispatch.py` (bonus catch) to use `core.llm_proxy`. Zero hardcoded proxy URLs remain in source outside canonical modules. (Cycle 60)

### P1 — MCP Client Test Coverage

- [x] [BUILD] Add social-media client unit tests — 15 new tests: `schedule_post()` (5), `get_post_analytics()` (2), error handling (7: 5xx, 4xx, timeout, connection error across methods), data envelope unwrapping (1). 38 total tests, all mocked HTTP. (Cycle 61)
- [x] [BUILD] Add genpeli client unit tests — 24 total tests (14 new): `process_video()`, `check_status()`, `get_preview()`, `approve()`, `reject()`, `health()`. Error handling (7: timeout, 404, 5xx, 4xx, connection errors), retry behavior (1), client lifecycle (2), Pydantic models (4). All mocked HTTP. (Cycle 62)
- [x] [BUILD] Add pilaster client unit tests — 28 total tests (7 new error handling): timeout on generate_image, connection error on generate_image, 404 on get_characters, 5xx on get_templates, 4xx on query_experiments, timeout on get_successful_prompts, connection error on health. Uses `__wrapped__` to bypass tenacity retry. All mocked HTTP. (Cycle 63)

### P2 — API Route Test Coverage

- [x] [BUILD] Add Observatory API route tests — 33 new tests covering content detail/PATCH/calendar, alerts (regression/stalls/filter), improvement (score-trends/bandit-arms/gaps/drift/summary), results, config (GET/PUT), knowledge (memory/lessons). 66 total Observatory API tests. (Cycle 64)

### P3 — Carry-Forward (Blocked)

- [~] [REVIEW] First real agent run — **BLOCKED: ANTHROPIC_API_KEY needed.** Carried from Sprint 3.
- [~] [BUILD] Prompt tuning based on first run — **BLOCKED: Depends on first real run.** Carried from Sprint 3.
- [~] [REVIEW] Brand.yaml completion — **BLOCKED: Needs Camilo session.** Review brief at `data/brand-review-brief.md`. Carried from Sprint 3.

---

## Sprint 6: Code Quality & Critical Test Coverage

Goal: Fix all lint errors, add tests for the most critical untested modules (Claude API client, agent base class,
events system), and reduce mypy error count. Clean codebase = faster future development.

**Key context:**
- 1272 tests passing, 27 lint errors (10 auto-fixable), 135 mypy errors
- 31 source files with zero test coverage — 4 critical (claude_api/client, agents/base, core/events, core/process_manager)
- 3 blocked items carry forward (API key, prompt tuning, brand.yaml)

### P0 — Lint Cleanup

- [x] [BUILD] Auto-fix lint errors — `ruff check --fix` fixed 10 errors (F401, I001, UP024, RUF022). (Cycle 65)
- [x] [BUILD] Fix manual lint errors — Fixed 17 errors: N802 (7 test names lowercased), B007 (4 `_i` renames), F841 (2 unused vars removed), RUF012 (2 ClassVar annotations), SIM108 (1 ternary), TC003 (1 TYPE_CHECKING). Zero lint errors remain. (Cycle 65)

### P1 — Critical Module Tests

- [x] [BUILD] Add Claude API client unit tests — 34 new tests: CachedPrompt (6), client init/routing (4), tool handling (2), extended thinking (2), cost tracking (5), cost math (3), batch API (3), define_tool (2), tool loop (5), pricing table (3). All mocked. (Cycle 65)
- [ ] [BUILD] Add agent base class unit tests — `src/holus/agents/base.py` (371 LOC). Test lifecycle methods, config loading, error handling patterns.
- [ ] [BUILD] Add events system unit tests — `src/holus/core/events.py` (253 LOC). Test pub/sub, event routing, Redis fallback.
- [ ] [BUILD] Add process manager unit tests — `src/holus/core/process_manager.py` (248 LOC). Test process lifecycle, timeout handling, cleanup.

### P2 — Mypy Error Reduction

- [ ] [BUILD] Fix idea_runner.py type errors — 20 mypy errors: add dict type params, fix untyped object access.
- [ ] [BUILD] Fix agent.py type errors — 30 mypy errors: return type annotations, Any-return issues.
- [ ] [BUILD] Fix prompt_evolution.py type errors — 2 mypy errors: missing `agenerate` method.

### P3 — Carry-Forward (Blocked)

- [~] [REVIEW] First real agent run — **BLOCKED: ANTHROPIC_API_KEY needed.** Carried from Sprint 3.
- [~] [BUILD] Prompt tuning based on first run — **BLOCKED: Depends on first real run.** Carried from Sprint 3.
- [~] [REVIEW] Brand.yaml completion — **BLOCKED: Needs Camilo session.** Review brief at `data/brand-review-brief.md`. Carried from Sprint 3.
