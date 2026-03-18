# Roadmap -- Holus

_Last updated: 2026-03-17_

## Now (current focus)

- [ ] Fix Instagram rubric — caption scored 0.40 despite hook 9/10 and voice PASS. Rubric miscalibrated for short-form
- [ ] Wire auto-publish approval flow — 36 items processed as `skipped`, need approval gate or config for autonomous publishing
- [ ] Observatory frontend polish (chart components, SSE real-time, accessibility) -- spec 029
- [ ] Silo integration hardening (genpeli MCP, pilaster MCP, social-media MCP) -- specs 014-016
- [ ] End-to-end publish test — generate → approve → publish → verify post appears on social media

## Next (after Now is done)

- Prompt optimizer pipeline: A/B testing, versioned variants in `config/prompts/` -- spec 030
- Observatory alerts: Slack/Telegram notifications on quality drops or cost spikes
- Blog publishing pipeline: SEO researcher → blog writer → portfolio /blog route
- Coordinator agent: cross-product pattern synthesis (needs 2+ months of data) -- spec 006
- Langfuse tracing integration for production observability

## Later (3-6 months, directional)

- DSPy MIPROv2 monthly prompt optimization from Langfuse training data
- TextGrad test-time refinement for individual outputs
- Cognee knowledge graph for cross-project relationships
- Automated weekly performance attribution reports

## Never

- **Local LLM inference for reasoning** -- we use cloud Claude. Local models are only for classification. Intelligence quality is the primary constraint, not cost.
- **Real-time / HFT trading** -- Holus is marketing only. Trading is pythia + milo, completely separate.
- **General-purpose chatbot** -- Holus is headless. No conversational UI, no chat interface.
- **Unified real-time orchestrator** -- coordinator runs daily. Real-time orchestration reintroduces compound errors.

## Done

### Sprint 5: Self-Improving Content Engine (2026-03-17)

10 implementation sprints + final wiring. 32 commits, 811 tests passing.
First live content cycle: 4 pieces generated, 3/4 passed judge (LinkedIn 0.97, Twitter 0.96, Threads 0.94).

- [x] **Sprint 0**: Research overhaul — self-improvement.md (6 mechanisms, 7 papers, 505 lines)
- [x] **Sprint 1** (14 tasks): Core wiring — JudgeAgent in pipeline, auto-publish, analytics collector, PromptLoader, reflexion, gap detector, drift detection, cron orchestration
- [x] **Sprint 2**: Thompson Sampling — Bayesian bandit for content strategy decisions
- [x] **Sprint 3**: Genetic prompt evolution — PromptBreeder population management
- [x] **Sprint 4**: Specialist dispatch — component evaluation, parallel execution, orchestrator
- [x] **Sprint 5**: DSPy bridge — few-shot bootstrapping, optimizer stubs, SQLite trajectory DB
- [x] **Sprint 6**: Observatory self-improvement API — failure taxonomy, cost ratio, anomaly detection, A/B stats
- [x] **Sprint 7**: Platform isolation — platform-specific config, cross-platform repurposing, normalization
- [x] **Sprint 8**: Human feedback loop — judge calibration, preference learning
- [x] **Sprint 9**: Constitutional AI — revision loop, voice checker, competitor analysis, trending detection
- [x] **Sprint 10**: Resilience & ops — retry/fallback/circuit breaker, load test (100 pieces/day), security checklist, autonomous operations runbook
- [x] **Wiring**: Justfile commands (`just content-cycle`), revision loop sync, platform rubrics
- [x] **Fix**: Judge proxy routing, sync revision methods, pipeline runs end-to-end

### Sprint 4.5: Visual Pipeline & Carousel (2026-03-15 — 2026-03-17)

- [x] Carousel PDF pipeline with premium dark design system
- [x] 5 named themes, 7 slide layouts, gradient system, visual effects CSS
- [x] 4 font pairings (tech, editorial, modern, bold)
- [x] Agent-driven design selection (LLM picks theme, fonts, gradient, effect)
- [x] SVG chart generators (sparkline, bar, donut, decorative)
- [x] Auto-inject SVGs into stat and split slides
- [x] E2e carousel rendering tests (6 tests, real Chromium)
- [x] Visual pipeline integration in LangGraph (render node + publish)
- [x] Poll support + video skeleton
- [x] LinkedIn content playbook — no standalone text posts

### Sprint 4: Agent Intelligence & Observatory (2026-03-12)

- [x] Agent registry: AGENTS.yaml with 32 agents, AgentRegistry class, PromptLoader 3-layer resolution -- spec 030
- [x] 32 agent prompt files: 22 specialists (6 content categories) + 7 domain-expert evaluators + 2 ops + 1 manager
- [x] Observatory API: FastAPI with 12 endpoints, SSE streaming, file-based data -- spec 028
- [x] Observatory frontend: Next.js 15 scaffold with 6 pages, 10 components -- spec 029
- [x] Self-improvement wiring: judge dispatcher, evaluator routing, BaseAgent hooks -- spec 030
- [x] Documentation: domain.md, ADR-0005, evaluations playbook, observability playbook, vision refresh
- [x] CVE fix: langgraph 1.0.9 → 1.1.2 (CVE-2026-28277)

### Sprint 3: Resilient Infrastructure (2026-03-11)

- [x] Resilient agent loop: CycleState machine, health preflight, trajectory contract -- spec 027
- [x] Quality gate enforcement + dead man's switch -- spec 027
- [x] Error recovery: retry logic, partial state save, phase-granular errors -- spec 027
- [x] Content quality scoring gate before review queue
- [x] E2e publish pipeline test

### Sprint 2: Authority Engine (2026-03-09)

- [x] Brand.yaml config loader -- spec 017
- [x] Marketing prompts rewrite for authority-building framing -- spec 017
- [x] Niche research step in observe stage (web search → insight extraction) -- spec 017
- [x] Content repurposing logic -- spec 017
- [x] Analytics feedback to marketing agent observe stage
- [x] Weekly content calendar view
- [x] Social-media-automatization client (replaced Late API) -- spec 016
- [x] Dry-run mode for publishing pipeline
- [x] launchd plists with absolute paths

### Sprint 1: Core Infrastructure (2026-02-25)

- [x] Project initialized with full fleet standard
- [x] Configuration management (pydantic-settings + YAML + env vars) -- spec 001
- [x] Claude API client with prompt caching -- spec 001
- [x] Kill switch system (per-agent, per-domain, global) -- spec 001
- [x] Event bus (Redis pub/sub) -- spec 001
- [x] Marketing agent ReAct loop (observe → reason → act → evaluate) -- spec 010
- [x] Knowledge & learning system -- spec 012
- [x] Scheduling & runtime foundations -- spec 013
