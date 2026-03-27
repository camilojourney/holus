# Phase 2: Attack Every Gap — 60 Parallel Agents

**Goal:** Every gap found in Phase 1 + every known gap from specs gets fixed simultaneously.
**Done when:** All untested modules have tests, all stubs resolved, all frontend wired, all dead code removed.

## Track A: Test Coverage (20 agents via /code)

Each agent writes tests for exactly ONE source file. No agent touches more than one module.

| # | Agent | Target File | Lines | What to Test |
|---|-------|-------------|-------|-------------|
| A1 | `test-orchestrator` | agents/marketing/orchestrator.py | 253 | content_cycle, analytics_cycle, improvement_cycle with mocked deps |
| A2 | `test-content-gen` | agents/marketing/content_generator.py | 308 | Multi-variant generation, platform formatting, error handling |
| A3 | `test-corpus` | data/corpus.py | 323 | SQLite FTS ingest, search, top_by_engagement, empty db edge cases |
| A4 | `test-content-api` | api/routes/content.py | 336 | GET /content, GET /content/{id}, PATCH approve/reject |
| A5 | `test-agents-api` | api/routes/agents.py | 191 | GET /agents, GET /agents/{id}, status filtering |
| A6 | `test-trajectory-api` | api/routes/trajectory.py | 149 | GET /trajectory, SSE streaming, pagination |
| A7 | `test-evaluations-api` | api/routes/evaluations.py | 148 | GET /evaluations, filtering by verdict |
| A8 | `test-health-api` | api/routes/health.py | 174 | GET /health, kill switch status |
| A9 | `test-knowledge-api` | api/routes/knowledge.py | 153 | GET /knowledge, file listing, freshness |
| A10 | `test-results-api` | api/routes/results.py | 47 | GET /results (may be a stub — verify first) |
| A11 | `test-improvement-api` | api/routes/improvement.py | 211 | GET /improvement, learning loop state |
| A12 | `test-genpeli-client` | integrations/genpeli/client.py | 226 | HTTP calls mocked, poll logic, timeout handling |
| A13 | `test-pilaster-client` | integrations/pilaster/client.py | 253 | Recipe submission, experiment query, template fetch |
| A14 | `test-dspy-optimizer` | self_improvement/dspy_optimizer.py | 145 | Optimization loop, metric tracking |
| A15 | `test-revision-loop` | agents/marketing/revision_loop.py | 176 | Revision pipeline, max iterations, quality improvement |
| A16 | `test-card-gen` | agents/marketing/card_generator.py | 256 | Card rendering, brand compliance |
| A17 | `test-perf-loop` | agents/marketing/performance_loop.py | 110 | 48h read-back, reward calculation |
| A18 | `test-visual-pipeline` | agents/marketing/visual_pipeline.py | 262 | Image/carousel generation dispatch |
| A19 | `test-voice-pipeline` | agents/marketing/voice_pipeline.py | 271 | Idea injection → context → voice writing flow |
| A20 | `test-mcp-server` | mcp/server.py | 227 | Tool registration, request handling |

## Track B: Implementation (15 agents via /code)

Each agent implements or completes ONE module. Reads the relevant spec first.

| # | Agent | Target | Spec | What to Do |
|---|-------|--------|------|-----------|
| B1 | `impl-diagnostician` | self_improvement/diagnostician.py | 036 | Complete pattern detection, root cause tracing, NEXT.md task generation |
| B2 | `impl-judge-calibration` | self_improvement/judge_calibration.py | 030 | Inter-rater reliability, score normalization, calibration metrics |
| B3 | `impl-bandit` | agents/marketing/bandit.py | 035 | Thompson sampling, state persistence, arm selection |
| B4 | `impl-perf-loop` | agents/marketing/performance_loop.py | 035 | 48-hour analytics read-back, reward computation, bandit update |
| B5 | `impl-telegram-gate` | api/routes/telegram_gate.py | 035 | Inline keyboard approval, webhook handler, state tracking |
| B6 | `impl-cli` | __main__.py | 013 | `python -m holus run/status/kill/health` CLI commands |
| B7 | `impl-visual-registry` | visual/registry.py (NEW) | 034 | Creative tool registry, treatment selection, token loading |
| B8 | `impl-langfuse` | observability/langfuse_client.py | 001 | Wire into llm_proxy for automatic tracing |
| B9 | `impl-mem0` | memory/mem0_client.py | 012 | Wire into marketing agent observe phase |
| B10 | `impl-ci` | .github/workflows/ci.yml (NEW) | - | GitHub Actions: just check on PRs, coverage report |
| B11 | `impl-env-example` | .env.example (NEW) | 001 | Every required variable documented |
| B12 | `impl-preflight` | preflight.py | 013 | Verify all services, API keys, MCP connections |
| B13 | `impl-seo-agent` | agents/specialists/research/seo-strategist.md | 017 | Complete the PLANNED agent prompt with KERNEL template |
| B14 | `impl-audience-agent` | agents/specialists/research/audience-analyst.md | 017 | Complete the PLANNED agent prompt with KERNEL template |
| B15 | `impl-competitive-agent` | agents/specialists/research/competitive-intel.md | 017 | Complete the PLANNED agent prompt with KERNEL template |

## Track C: Frontend Wiring (15 agents via /ux)

Each agent wires ONE page to the real Observatory API. Removes demo-data dependency.

| # | Agent | Target Page | API Endpoint | What to Wire |
|---|-------|------------|-------------|-------------|
| C1 | `ux-dashboard` | app/page.tsx | /api/v1/health, /api/v1/results | KPIs, system health, agent feed |
| C2 | `ux-agents` | app/agents/page.tsx | /api/v1/agents | Agent grid from AGENTS.yaml |
| C3 | `ux-agent-detail` | app/agents/[id]/page.tsx | /api/v1/agents/{id} | Performance chart, cycle history |
| C4 | `ux-content` | app/content/page.tsx | /api/v1/content | Kanban board with real queue |
| C5 | `ux-evaluations` | app/evaluations/page.tsx | /api/v1/evaluations | Heatmap with proper color scaling |
| C6 | `ux-health` | app/health/page.tsx | /api/v1/health | Kill switch banner, service status |
| C7 | `ux-knowledge` | app/knowledge/page.tsx | /api/v1/knowledge | File tree, freshness indicators |
| C8 | `ux-trajectory` | TrajectoryTimeline.tsx | /api/v1/trajectory (SSE) | Real-time event stream |
| C9 | `ux-results` | app/results/page.tsx | /api/v1/results | Cost, quality, success rate charts |
| C10 | `ux-followers` | app/followers/page.tsx | /api/v1/results | Growth trend chart |
| C11 | `ux-engagement` | app/engagement/page.tsx | /api/v1/results | Platform-level engagement |
| C12 | `ux-improvement` | (NEW page) | /api/v1/improvement | Learning loop state, lessons |
| C13 | `ux-about` | app/about/page.tsx | static | System architecture, version info |
| C14 | `ux-dark-mode` | globals.css + all components | - | WCAG AA contrast audit + fix |
| C15 | `ux-mobile` | all pages | - | 375px viewport audit + fix |

## Track D: Dead Code & Coherence Fixes (10 agents)

Based on Phase 1 audit findings. These agents clean up what shouldn't exist.

| # | Agent | Task | Skill |
|---|-------|------|-------|
| D1 | `clean-stub-agents` | Delete or implement stub agents (coding, content, coordinator, pilaster) — based on Phase 1 verdict | `/code holus` |
| D2 | `clean-stub-integrations` | Delete comfyui/ and n8n/ empty stubs if unused | `/code holus` |
| D3 | `clean-duplicate-bandit` | Resolve bandit.py vs strategy_bandit.py — consolidate into one | `/code holus` |
| D4 | `clean-duplicate-charts` | Resolve charts.py vs chart.py — consolidate or clarify purpose | `/code holus` |
| D5 | `clean-prompt-files` | Resolve prompts.py vs prompt_loader 3-layer system — remove redundancy | `/code holus` |
| D6 | `clean-optimization-files` | Resolve dspy_bridge vs dspy_optimizer vs prompt_optimizer vs prompt_evolution — consolidate | `/code holus` |
| D7 | `clean-llm-proxy` | Resolve llm_proxy.py vs claude_api/client.py — consolidate or clarify | `/code holus` |
| D8 | `clean-failed-file` | Fix corrupted .failed file (100+ placeholder entries) | `/code holus` |
| D9 | `clean-stale-docs` | Update NEXT.md, sprint-state.json, stale playbooks | `/maintenance holus` |
| D10 | `clean-mypy-overrides` | Resolve 9 modules with relaxed type checking | `/maintenance holus` |

## Internal Loop

After all tracks complete:
1. Run `just check` — lint + types + tests
2. If failures: launch targeted fix agents (max 5)
3. Re-run `just check`
4. Max 2 fix iterations

## Output

- `results/phase-02-track-a-tests.md` — new test files created, coverage delta
- `results/phase-02-track-b-impl.md` — modules implemented/completed
- `results/phase-02-track-c-frontend.md` — pages wired, demo-data removed
- `results/phase-02-track-d-cleanup.md` — files deleted, duplicates resolved
- `results/phase-02-check-results.md` — just check output

## Feeds into

Phase 3 reviews the complete, cleaned, tested codebase.
