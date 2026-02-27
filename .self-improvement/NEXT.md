# Holus Priority Queue

80-cycle autonomous build sprint. Each task = 1 cycle (~15-45 min).
Tasks are tagged: `[BUILD]` `[RESEARCH]` `[INTEGRATE]` `[REVIEW]` `[CREATE]`

The builder uses Codex for coding, Gemini for research, Claude for orchestration.

---

## P0 — Foundation (Cycles 1-8) ✓

- [x] `[BUILD]` Create `src/holus/__main__.py` CLI entrypoint with run/status/kill/health commands (spec 013 SPEC-001)
- [x] `[BUILD]` Create `src/holus/core/run_lock.py` file-based lock with flock (spec 009 SPEC-003)
- [x] `[BUILD]` Create `src/holus/memory/trajectory.py` TrajectoryLogger — append, read, filter, summary (spec 012 SPEC-002) — already existed
- [x] `[BUILD]` Create `src/holus/core/health.py` health check system (spec 013 SPEC-003)
- [x] `[BUILD]` Wire justfile: `run-marketing`, `schedule`, `unschedule`, `schedule-status`, `health`, `rotate-logs` (spec 013)
- [x] `[BUILD]` Create `infra/launchd/` with marketing, improve, and health plist files (spec 013 SPEC-002)
- [x] `[BUILD]` Create unit tests for run_lock, trajectory logger, and health check — 22 tests passing
- [x] `[REVIEW]` Run `just check` on all P0 work — fix any lint/type/test failures

## P1 — Marketing Agent Core (Cycles 9-20) ✓

- [x] `[BUILD]` Create `src/holus/agents/marketing/__init__.py` and `models.py` — ContentDecision, GeneratedPiece, MarketingCycleReport (spec 010)
- [x] `[BUILD]` Create `src/holus/agents/marketing/prompts.py` — system prompts for Opus strategy + Sonnet content generation (spec 010)
- [x] `[BUILD]` Create `src/holus/agents/marketing/agent.py` — MarketingAgent with LangGraph ReAct loop: observe → reason → act → evaluate (spec 010 SPEC-001)
- [x] `[BUILD]` Implement observe stage — read products.yaml, knowledge files, MEMORY.md (spec 010 SPEC-002)
- [x] `[BUILD]` Implement reason stage — Opus strategy decisions with structured ContentDecision output (spec 010 SPEC-003)
- [x] `[BUILD]` Implement act stage — Sonnet text generation per platform, save to content queue (spec 010 SPEC-004)
- [x] `[BUILD]` Implement evaluate stage — log to trajectory.jsonl with full metadata (spec 010 SPEC-005)
- [x] `[BUILD]` Create `src/holus/agents/marketing/run.py` entrypoint + `config/marketing_agent.yaml` (already exists)
- [x] `[BUILD]` Create unit tests for marketing agent — mock Claude API, test each stage independently (26 tests passing)
- [x] `[BUILD]` Create `data/content-queue/` with .gitignore, content queue save/load functions (queue logic in agent.py)
- [x] `[REVIEW]` Run full `just check`, fix issues, commit all marketing agent code (74 tests passing, ruff clean)
- [x] `[REVIEW]` Security review completed — no vulnerabilities found, follows best practices

## P2 — Social Media Integration (Cycles 21-30)

- [ ] `[RESEARCH]` Gemini: research Late.so API — endpoints, auth, rate limits, scheduling, analytics. Write to knowledge/current/late-api.md
- [ ] `[BUILD]` Create `src/holus/integrations/late_api/client.py` — publish, get_analytics, get_scheduled (spec 011 SPEC-001)
- [ ] `[BUILD]` Create `src/holus/agents/marketing/content_queue.py` — enqueue, list_pending, approve, reject (spec 011 SPEC-003)
- [ ] `[BUILD]` Create `src/holus/agents/marketing/review.py` — CLI for reviewing/approving content
- [ ] `[BUILD]` Create `src/holus/agents/marketing/publish_approved.py` — publish approved content via Late API
- [ ] `[BUILD]` Wire justfile: `review-content`, `approve-content`, `reject-content`, `publish-approved`
- [ ] `[BUILD]` Create `src/holus/mcp_servers/__init__.py` and `social_media.py` — MCP server wrapping Late API (spec 011 SPEC-002)
- [ ] `[BUILD]` Create unit tests for Late API client, content queue, and MCP server (mock httpx)
- [ ] `[REVIEW]` Run `just check`, fix issues, Gemini reviews all social media integration code
- [ ] `[CREATE]` Analyze what's missing — add new tasks if Late API doesn't support something we need

## P3 — Repo Exploration & Research (Cycles 31-40)

- [ ] `[RESEARCH]` Gemini: deep-dive into `/Users/mini/.openclaw/workspace/github/social-media-automatization/` — architecture, APIs, DB schema, how it posts, analytics storage. Write findings to knowledge/current/social-media-repo.md
- [ ] `[RESEARCH]` Gemini: deep-dive into `/Users/mini/.openclaw/workspace/github/genpeli/` — video pipeline, APIs, MCP server if any, what tools it exposes. Write to knowledge/current/genpeli-repo.md
- [ ] `[RESEARCH]` Gemini: deep-dive into `/Users/mini/.openclaw/workspace/github/pilaster/` — image generation, ComfyUI workflows, APIs, what Holus can call. Write to knowledge/current/pilaster-repo.md
- [ ] `[RESEARCH]` Gemini: research best carousel creation tools/libraries for LinkedIn + Instagram. How to generate carousels programmatically (PDF slides, image sequences). Write to knowledge/current/carousel-creation.md
- [ ] `[RESEARCH]` Gemini: research image generation APIs — Replicate Flux models, pricing, quality comparison. Best models for marketing images. Write to knowledge/current/image-generation-apis.md
- [ ] `[RESEARCH]` Gemini: research video generation APIs — Kling, Runway, Minimax, Creatomate. Cost, quality, speed comparison for short-form marketing videos. Write to knowledge/current/video-generation-apis.md
- [ ] `[CREATE]` Based on all research: create spec 014 for genpeli integration, spec 015 for pilaster integration, spec 016 for social-media-automatization integration
- [ ] `[CREATE]` Based on research: add 10-15 new integration tasks to NEXT.md for connecting to each repo
- [ ] `[CREATE]` Based on research: identify what content types are possible NOW vs what needs new tooling, add tasks
- [ ] `[REVIEW]` Review all knowledge files for accuracy and completeness. Update confidence levels.

## P4 — Silo Integrations (Cycles 41-55)

- [ ] `[INTEGRATE]` Connect to social-media-automatization: create API client or MCP client based on P3 research
- [ ] `[INTEGRATE]` Connect to genpeli: create API client or MCP client for video creation based on P3 research
- [ ] `[INTEGRATE]` Connect to pilaster: create API client or MCP client for image generation based on P3 research
- [ ] `[BUILD]` Create `src/holus/integrations/genpeli/client.py` — video creation client
- [ ] `[BUILD]` Create `src/holus/integrations/pilaster/client.py` — image generation client
- [ ] `[BUILD]` Create `src/holus/integrations/social_media/client.py` — direct social media client (fallback for Late API)
- [ ] `[BUILD]` If needed: create MCP server stubs in the silo repos (genpeli-mcp, pilaster-mcp)
- [ ] `[BUILD]` Update marketing agent act stage to use image generation (Pilaster/Replicate) for visual posts
- [ ] `[BUILD]` Update marketing agent to generate carousels (image sequences + text for LinkedIn/Instagram)
- [ ] `[BUILD]` Update marketing agent to request videos from genpeli for TikTok/Reels content
- [ ] `[BUILD]` Create content type handlers: text_post, image_post, carousel, thread, video_reel
- [ ] `[BUILD]` Create unit tests for all integration clients
- [ ] `[BUILD]` Create unit tests for all content type handlers
- [ ] `[REVIEW]` Full integration review: Gemini reviews all silo integration code
- [ ] `[REVIEW]` Run `just check` on everything, fix all issues

## P5 — Knowledge & Learning (Cycles 56-63)

- [ ] `[BUILD]` Create `src/holus/memory/knowledge_gaps.py` — knowledge gap request system (spec 012 SPEC-004)
- [ ] `[BUILD]` Create `src/holus/agents/marketing/learning.py` — weekly learning loop with pattern extraction (spec 012 SPEC-003)
- [ ] `[BUILD]` Implement MEMORY.md auto-update — Opus analyzes trajectory, writes new insights
- [ ] `[BUILD]` Implement knowledge file rotation — archive old versions, update current
- [ ] `[BUILD]` Create `.self-improvement/knowledge/current/performance-patterns.md` template (auto-updated by learning loop)
- [ ] `[BUILD]` Create unit tests for knowledge gaps, learning loop, and knowledge rotation
- [ ] `[REVIEW]` Run `just check`, fix issues
- [ ] `[CREATE]` After seeing trajectory data: identify what additional knowledge the agent needs, add research tasks

## P6 — Content Expansion (Cycles 64-72)

- [ ] `[RESEARCH]` Gemini: how to create LinkedIn carousels programmatically — PDF generation, image composition, tools available
- [ ] `[RESEARCH]` Gemini: how to create Instagram Reels with AI — best practices, tools, what genpeli can do
- [ ] `[BUILD]` Create `src/holus/agents/marketing/content_types/carousel.py` — generate multi-slide carousels for LinkedIn/Instagram
- [ ] `[BUILD]` Create `src/holus/agents/marketing/content_types/thread.py` — generate Twitter/X threads with proper formatting
- [ ] `[BUILD]` Create `src/holus/agents/marketing/content_types/video_brief.py` — generate video briefs for genpeli
- [ ] `[BUILD]` Create `src/holus/agents/marketing/content_types/image_post.py` — generate image posts via Pilaster/Replicate
- [ ] `[BUILD]` Update marketing agent to select content type based on platform + strategy
- [ ] `[BUILD]` Create tests for all content type generators
- [ ] `[REVIEW]` Full review of all content type code — Gemini checks quality, Codex checks patterns

## P7 — Analytics Database & Tracking (Cycles 73-82)

- [ ] `[RESEARCH]` Gemini: explore social-media-automatization DB schema — what tables exist, how to add a posts tracking table. Write findings to knowledge/current/analytics-database.md
- [ ] `[BUILD]` Design analytics database schema: posts table (post_id, platform, content_type, product, text, media_urls, posted_at, status), metrics table (post_id, platform, impressions, engagement_rate, clicks, shares, saves, follower_delta, measured_at)
- [ ] `[BUILD]` Create `src/holus/memory/analytics_db.py` — SQLite-based local analytics database (no external DB dependency for Phase 1). Functions: insert_post, update_metrics, get_post_performance, get_best_posts, get_platform_stats
- [ ] `[BUILD]` Create migration script `infra/db/init_analytics.py` to set up the SQLite database
- [ ] `[BUILD]` Wire analytics DB into marketing agent evaluate stage — every post tracked with full metadata
- [ ] `[BUILD]` Create `src/holus/agents/marketing/analytics.py` — weekly analytics analysis. Query DB, find patterns, report what's working
- [ ] `[BUILD]` Create justfile command `just analytics` to show analytics dashboard (top posts, platform comparison, content type performance)
- [ ] `[BUILD]` Create unit tests for analytics_db and analytics module
- [ ] `[REVIEW]` Run `just check`, fix issues
- [ ] `[CREATE]` Based on analytics schema: identify what metrics we can't track yet, add tasks to integrate with platform APIs

## P8 — Competitive Analysis & Niche Research (Cycles 83-90)

- [ ] `[RESEARCH]` Gemini: analyze top LinkedIn creators in AI tools niche — who gets the most engagement, what post types they use, their hook patterns. Write to knowledge/current/competitor-analysis.md
- [ ] `[RESEARCH]` Gemini: analyze top TikTok creators in AI/tech tools — viral patterns, hook styles, video formats. Add to competitor-analysis.md
- [ ] `[RESEARCH]` Gemini: research "viral framework extraction" — how to reverse-engineer why posts go viral, what patterns to look for (hook types, emotional triggers, CTA patterns). Write to knowledge/current/viral-frameworks.md
- [ ] `[BUILD]` Create `src/holus/agents/marketing/niche_analyzer.py` — reads competitor content (via Gemini web search), extracts frameworks, updates knowledge base
- [ ] `[BUILD]` Create `src/holus/agents/marketing/hook_generator.py` — generates scroll-stopping hooks based on proven viral patterns from knowledge/current/viral-frameworks.md
- [ ] `[BUILD]` Create `src/holus/agents/marketing/voice_profile.py` — analyzes founder's existing content to build a voice profile (tone, vocabulary, style patterns). Stores in knowledge/current/voice-profile.md
- [ ] `[BUILD]` Update marketing agent reason stage to use competitive insights and viral frameworks when deciding content
- [ ] `[BUILD]` Update marketing agent act stage to use hook_generator for every post's first line / first 3 seconds

## P9 — AI Performance Analysis (Cycles 91-98)

- [ ] `[BUILD]` Create `src/holus/agents/marketing/sprint_analyzer.py` — reads all trajectory.jsonl entries + analytics DB, produces comprehensive sprint report
- [ ] `[BUILD]` Sprint analyzer: which tools worked (Codex vs Gemini vs Claude solo), which failed, success rates per tool
- [ ] `[BUILD]` Sprint analyzer: which content types got built, which are working, which need improvement
- [ ] `[BUILD]` Sprint analyzer: cost analysis — total API spend, cost per content piece, cost per engagement
- [ ] `[BUILD]` Sprint analyzer: cross-repo change summary — what was changed in sibling repos, what's the impact
- [ ] `[BUILD]` Create `just sprint-report` command that generates the full analysis to `.self-improvement/reports/builder/sprint-analysis-YYYY-MM-DD.md`
- [ ] `[CREATE]` Based on sprint analysis: identify top 10 improvements, create P10 tasks
- [ ] `[REVIEW]` Full codebase review: Gemini reads entire src/holus/, all sibling repo changes, all knowledge files. Reports quality issues, security concerns, missing tests, architectural improvements.

## P10 — Manager Mode & Self-Direction (Cycles 99-105)

- [ ] `[BUILD]` End-to-end integration test: observe → reason → act (all content types) → evaluate → track in analytics DB
- [ ] `[BUILD]` Create `docs/playbooks/autonomous-operations.md` — how to run Holus, monitor, troubleshoot
- [ ] `[BUILD]` Update ARCHITECTURE.md to reflect current state — marketing engine, silo integrations, analytics DB
- [ ] `[BUILD]` Update AGENTS.md with marketing agent capabilities and integration status
- [ ] `[CREATE]` Manager cycle: analyze everything built in 100+ cycles, write comprehensive retrospective
- [ ] `[CREATE]` Manager cycle: identify next 20 tasks for continuous improvement, write them to NEXT.md P11+
- [ ] `[CREATE]` Manager cycle: propose new features based on what the growth engine vision needs that isn't built yet

---

## Previously Completed

- [x] Core infrastructure: config loading from YAML + env (src/holus/core/config.py)
- [x] Kill switch: Redis-backed, 3-scope (src/holus/core/kill_switch.py)
- [x] Event bus: Redis pub/sub + streams (src/holus/core/events.py)
- [x] Base agent class with LangGraph integration (src/holus/agents/base.py)
- [x] Knowledge base: platforms.md, audience-profiles.md, content-formats.md, content-marketing-strategy.md
- [x] Specs written: 009, 010, 011, 012, 013
- [x] Products config: config/products.yaml
- [x] Builder agent definition with Codex/Gemini delegation
- [x] Sprint script (infra/build-sprint.sh)

---

**Last updated:** 2026-02-26
**Updated by:** Human + Claude (80-cycle sprint setup)
