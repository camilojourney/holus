# Roadmap -- Holus

_Last updated: 2026-02-24_

## Now (current focus)

- [ ] Docker Compose service stack (PostgreSQL, Redis, n8n, Temporal, Langfuse) -- spec 001
- [ ] Configuration management (pydantic-settings + YAML + env vars) -- spec 001
- [ ] Claude API client with prompt caching -- spec 001
- [ ] Kill switch system (per-agent, per-domain, global) -- spec 001
- [ ] Event bus (Redis pub/sub + Streams) -- spec 001
- [ ] Trading agent: Signal Generator + Risk Manager + Execution Handler (paper) -- spec 002
- [ ] Trading agent: TradeMemory Protocol (L1/L2/L3) -- spec 002
- [ ] Coding agent: Claude Code CLI integration + CLAUDE.md per project
- [ ] Coding agent: GitHub Actions (PR review, weekly maintenance)

## Next (after Now is done)

- Content pipeline: text generation (Sonnet 4.5 + NeuronWriter) -- spec 003
- Content pipeline: image generation (ComfyUI + Replicate routing) -- spec 003
- Content pipeline: video generation (Kling AI + Creatomate) -- spec 003
- Content pipeline: distribution via Late API (13 platforms) -- spec 003
- Pilaster agent: ComfyUI API gateway + workflow version control
- Self-improvement loop: DSPy MIPROv2 monthly optimization
- Self-improvement loop: Reflexion for in-context learning
- Paper-to-live trading graduation (30-day minimum, codified criteria)

## Later (3-6 months, directional)

- Holus Coordinator agent: daily Opus synthesis across all agents
- Cognee knowledge graph for cross-project relationships
- Cross-project learning via shared event bus patterns
- TextGrad test-time refinement for individual outputs
- Performance feedback loop: content engagement -> strategy refinement
- Automated weekly performance attribution reports

## Never

- **Local LLM inference for reasoning** -- we use cloud Claude. Local models are only for classification (FinBERT). Intelligence quality is the primary constraint, not cost.
- **Real-time / HFT trading** -- we use daily/swing timeframes. Sub-second execution is a different system entirely.
- **General-purpose chatbot** -- Holus is headless. No conversational UI, no chat interface.
- **Multi-tenant SaaS** -- single founder, single portfolio. No user management.
- **Unified real-time orchestrator** -- coordinator runs daily. Real-time orchestration reintroduces compound errors.

## Done (last 3 months)

_(empty -- project is pre-implementation)_
