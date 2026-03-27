# Phase 1: Coherence Audit — Every File Has a Purpose

**Goal:** Read every file in the codebase. For each, answer: does it have a purpose, is it connected, should it exist?
**Done when:** Complete inventory with verdicts for all 130 Python files, 46 agent prompts, 41 frontend files, config, docs.

## Agent Assignments (40 agents)

### Python Source Auditors (28 agents)

Each agent reads its assigned files + checks imports (who imports this? what does this import?).

**Cluster 01** — Root entry points (5 files, 878 LOC)
`__init__.py, __main__.py, generate.py, evaluate_content.py, preflight.py`
Question: Are these the right entry points? Does __main__.py actually work? Is generate.py called by anything?

**Cluster 02** — Core state management (5 files)
`core/config.py, core/cycle_state.py, core/events.py, core/health.py, core/kill_switch.py`
Question: Are all 5 actually used in the agent loop? Is events.py wired to anything?

**Cluster 03** — Core process control (5 files)
`core/llm_proxy.py, core/multi_tenant.py, core/process_manager.py, core/prompt_loader.py, core/quality_gate.py`
Question: Is multi_tenant.py used (single-user system)? Is llm_proxy.py (55 LOC) a stub?

**Cluster 04** — Core resilience (4 files)
`core/resilience.py, core/retry.py, core/run_lock.py, core/watchdog.py`
Question: Are all 4 integrated into the marketing agent? Or sitting unused?

**Cluster 05** — API framework (3 files)
`api/app.py, api/models.py, api/routes/__init__.py`
Question: Does app.py mount all routes? Are models.py types used by routes?

**Cluster 06** — API routes A (5 files)
`routes/agents.py, routes/alerts.py, routes/config.py, routes/content.py, routes/evaluations.py`
Question: Does each route have a frontend page that calls it? Any orphan endpoints?

**Cluster 07** — API routes B (5 files)
`routes/health.py, routes/improvement.py, routes/ingest.py, routes/knowledge.py, routes/results.py`
Question: Is ingest.py receiving data from anywhere? Is results.py (47 LOC) a stub?

**Cluster 08** — API routes C (2 files)
`routes/telegram_gate.py, routes/trajectory.py`
Question: Is telegram_gate connected to a real Telegram bot? Does trajectory SSE work?

**Cluster 09** — Agent base (3 files)
`agents/__init__.py, agents/base.py, agents/registry.py`
Question: Does registry.py actually load from AGENTS.yaml? Is base.py subclassed correctly?

**Cluster 10** — Stub agents (5 files)
`agents/coding/agent.py, agents/content/agent.py, agents/coordinator/agent.py, agents/pilaster/agent.py`
Question: Are these stubs or real implementations? If stubs, should they be deleted until needed?

**Cluster 11** — Marketing core (4 files)
`marketing/__init__.py, marketing/agent.py, marketing/models.py, marketing/orchestrator.py`
Question: Is orchestrator.py the real entry point? Does agent.py call everything it should?

**Cluster 12** — Content generation pipeline (5 files)
`marketing/content_queue.py, marketing/content_generator.py, marketing/card_generator.py, marketing/humanize.py, marketing/format_planner.py`
Question: Does content flow through all 5 in order? Any broken handoffs?

**Cluster 13** — Idea pipeline (4 files)
`marketing/idea_runner.py, marketing/idea_utils.py, marketing/topic_index.py, marketing/strategy_bandit.py`
Question: Does idea_runner use strategy_bandit? Is topic_index populated?

**Cluster 14** — Publishing pipeline (5 files)
`marketing/auto_publish.py, marketing/publish_approved.py, marketing/platform_adapter.py, marketing/telegram_sender.py, marketing/analytics_collector.py`
Question: What's the difference between auto_publish and publish_approved? Redundancy?

**Cluster 15** — Quality pipeline (4 files)
`marketing/review.py, marketing/review_videos.py, marketing/quality_score.py, marketing/quality_compounding.py`
Question: Is quality_compounding.py used? Does review.py connect to quality_score.py?

**Cluster 16** — Media workflows (5 files)
`marketing/image_workflow.py, marketing/video_workflow.py, marketing/visual_pipeline.py, marketing/voice_pipeline.py, marketing/performance_loop.py`
Question: Are these all called from agent.py? Or are some dead?

**Cluster 17** — Marketing advanced (4 files)
`marketing/calendar_view.py, marketing/revision_loop.py, marketing/specialist_dispatch.py, marketing/prompts.py`
Question: Is prompts.py still needed with 3-layer prompt loader? Redundancy check.

**Cluster 18** — Marketing misc (3 files)
`marketing/bandit.py, marketing/platform_config.py, marketing/video_queue.py`
Question: bandit.py vs strategy_bandit.py — which is active? Duplicate?

**Cluster 19** — Integrations Claude + Genpeli (4 files)
`integrations/claude_api/client.py, integrations/genpeli/client.py + __init__.py files`
Question: Is claude_api/client.py the same as core/llm_proxy.py? Duplication?

**Cluster 20** — Integrations Pilaster + Social (4 files)
`integrations/pilaster/client.py, integrations/social_media/client.py + __init__.py files`
Question: Do these match what the MCP servers actually expose?

**Cluster 21** — Stub integrations + MCP (3 files)
`integrations/comfyui/__init__.py, integrations/n8n/__init__.py, mcp/server.py`
Question: comfyui and n8n are 1-line stubs. Delete? Is mcp/server.py functional?

**Cluster 22** — Memory module (5 files)
`memory/__init__.py, memory/knowledge.py, memory/knowledge_gaps.py, memory/mem0_client.py, memory/trajectory.py`
Question: Is mem0_client.py wired into anything? Or just a framework?

**Cluster 23** — Observability (3 files)
`observability/__init__.py, observability/langfuse_client.py, observability/otel.py`
Question: Is either actually collecting data? Or both frameworks waiting to be wired?

**Cluster 24** — Self-improvement judges (4 files)
`self_improvement/judge.py, self_improvement/judge_calibration.py, self_improvement/analytics.py, self_improvement/reflexion.py`
Question: Is reflexion.py connected to anything? Does judge_calibration.py work?

**Cluster 25** — Self-improvement learning (4 files)
`self_improvement/learning_loop.py, self_improvement/diagnostician.py, self_improvement/gap_detector.py, self_improvement/trajectory_db.py`
Question: Is diagnostician the spec-036 implementation or a different thing? Is gap_detector producing real requests?

**Cluster 26** — Self-improvement optimization (3 files)
`self_improvement/dspy_bridge.py, self_improvement/dspy_optimizer.py, self_improvement/prompt_optimizer.py, self_improvement/prompt_evolution.py`
Question: 4 files for prompt optimization — which is the real one? Consolidate?

**Cluster 27** — Visual core (5 files)
`visual/__init__.py, visual/engine.py, visual/models.py, visual/brand.py, visual/templates.py`
Question: Does engine.py power real visual generation? Or is it a framework?

**Cluster 28** — Visual rendering (5 files)
`visual/charts.py, visual/chart.py, visual/carousel_builder.py, visual/gif_encoder.py, visual/gradients.py`
Question: charts.py (830 LOC) vs chart.py (207 LOC) — duplication? Is gif_encoder used?

### Agent Prompt Auditors (5 agents)

**Cluster 29** — Manager + Content specialists (7 prompts)
`marketing-strategist.md, idea-generator.md, idea-planner.md, context-builder.md, voice-writer.md, idea-injector.md`
Question: Do these match what specialist_dispatch.py actually routes to?

**Cluster 30** — Written authority + Research specialists (9 prompts)
`hook-architect.md, storyteller.md, technical-translator.md, voice-guardian.md, cta-strategist.md, niche-researcher.md, seo-strategist.md, audience-analyst.md, competitive-intel.md`
Question: Are PLANNED agents (seo, audience, competitive) referenced anywhere in code?

**Cluster 31** — Visual + Video + Growth specialists (10 prompts)
All visual, video, and growth agent prompts
Question: Are video specialists connected to genpeli workflow? Are growth specialists used?

**Cluster 32** — Repurposing + Ops agents (5 prompts)
`bilingual-localizer.md, format-converter.md, platform-adapter.md, security-sentinel.md, knowledge-keeper.md`
Question: Is knowledge-keeper.md used or is it a manual-only agent?

**Cluster 33** — All 7 evaluator prompts
All evaluator .md files
Question: Do these match the evaluator routing in judge.py? Any evaluator defined in YAML but missing an .md file?

### Frontend Auditors (4 agents)

**Cluster 34** — Pages A (7 pages)
`page.tsx (home), agents/page.tsx, agents/[id]/page.tsx, content/page.tsx, evaluations/page.tsx, health/page.tsx, knowledge/page.tsx`
Question: Does each page fetch from the right API endpoint? Any using demo-data as primary?

**Cluster 35** — Pages B + Layout (6 pages)
`followers/page.tsx, engagement/page.tsx, results/page.tsx, about/page.tsx, layout.tsx, loading.tsx`
Question: Are followers/engagement pages using real social-media API data?

**Cluster 36** — Components A (10 components)
`Sidebar, ErrorBanner, KillSwitchBanner, FreshnessIndicator, KPICard, SystemHealthGrid, PlatformCard, PlatformDistribution, AgentCard, AgentSparkline`
Question: Is every component used by at least one page? Any orphans?

**Cluster 37** — Components B + Lib (10 components + 4 libs)
`QualityHeatmap, TrajectoryTimeline, TopPostRow, PillarBreakdown, GrowthChart, ContentKanban, ContentDetailPanel, HoverRow, RadioGroup, HolusLogo, types.ts, api.ts, sse.ts, demo-data.ts`
Question: Does api.ts match the actual Observatory API endpoints? Is sse.ts connected?

### Config + Docs Auditors (3 agents)

**Cluster 38** — All 9 config files
Question: Are all configs loaded by config.py? Any orphan YAML files?

**Cluster 39** — Docs decisions + playbooks (18 files)
Question: Are playbooks current? Any ADRs superseded by later decisions?

**Cluster 40** — .self-improvement + knowledge (15 files)
Question: Is NEXT.md current? Is sprint-state.json accurate? Are all 13 knowledge files used?

## Output

Each auditor produces a verdict per file:
- **ACTIVE** — real code, connected, has purpose
- **STUB** — skeleton/placeholder, could be deleted or implemented
- **ORPHAN** — not imported/used by anything
- **DUPLICATE** — another file does the same thing
- **STALE** — references things that no longer exist
- **BROKEN** — imports fail or logic is incorrect

Compiled into `results/phase-01-coherence-audit.md`.

## Feeds into

Phase 2 Track D (dead code cleanup) uses the STUB/ORPHAN/DUPLICATE/STALE verdicts.
Phase 2 Tracks A-C use ACTIVE verdicts to prioritize what to test and wire.
