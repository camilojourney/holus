# Roadmap -- Holus

_Last updated: 2026-03-12_

## Now (current focus)

- [ ] Wire self-improvement loop end-to-end (judge dispatcher, Langfuse tracing, learning loop scheduling) -- spec 030
- [ ] Observatory frontend polish (chart components, SSE real-time, accessibility) -- spec 029
- [ ] Silo integration hardening (genpeli MCP, pilaster MCP, social-media MCP) -- specs 014-016
- [ ] First live marketing cycle with judge evaluation (requires API keys + silo services)

## Next (after Now is done)

- Content factory v2: specialist spawner, adaptive threshold, reviewer pool -- specs 025-026
- Prompt optimizer pipeline: A/B testing, versioned variants in `config/prompts/` -- spec 030
- Observatory alerts: Slack/Telegram notifications on quality drops or cost spikes
- Blog publishing pipeline: SEO researcher → blog writer → portfolio /blog route
- Coordinator agent: cross-product pattern synthesis (needs 2+ months of data) -- spec 006

## Later (3-6 months, directional)

- DSPy MIPROv2 monthly prompt optimization from Langfuse training data
- Reflexion for in-context learning during content generation
- TextGrad test-time refinement for individual outputs
- Cognee knowledge graph for cross-project relationships
- Automated weekly performance attribution reports

## Never

- **Local LLM inference for reasoning** -- we use cloud Claude. Local models are only for classification. Intelligence quality is the primary constraint, not cost.
- **Real-time / HFT trading** -- Holus is marketing only. Trading is pythia + milo, completely separate.
- **General-purpose chatbot** -- Holus is headless. No conversational UI, no chat interface.
- **Multi-tenant SaaS** -- single founder, single portfolio. No user management.
- **Unified real-time orchestrator** -- coordinator runs daily. Real-time orchestration reintroduces compound errors.

## Done

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
