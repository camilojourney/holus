# Domain Profile: holus

## Domain

AI marketing strategist for a solo founder's product portfolio. An episodic agent system that observes social media analytics, decides what content to create, briefs specialized silo tools (genpeli for video, pilaster for images, social-media-automatization for publishing), and learns from results to improve strategy over time. Not a chatbot or unified codebase — a headless operational system triggered by schedules and webhooks.

## Non-Obvious Constraints

- **Holus is the brain, not the hands.** Holus decides strategy and briefs silo tools via MCP. It never generates videos (genpeli does that), generates images (pilaster does that), or publishes content (social-media-automatization does that). Attempting to add execution capabilities to Holus breaks the federated architecture.
- **Data never lives in Holus permanently.** Analytics data stays in social-media-automatization. Image files stay in pilaster's R2. Video files stay in genpeli's storage. Holus reads silo data to make decisions but never stores it. The source of truth is always the silo.
- **Trading systems are completely isolated.** pythia and milo-to-the-moon are never referenced, called, or monitored by Holus. They are separate businesses. Never build connections between Holus and trading repos.
- **Human approval is required for publishing in Phase 1.** All publish actions via social-media MCP require human review before execution. Autonomous publishing only begins in Phase 2+ with weekly human review.
- **guardrails.yaml is a protected file.** `config/guardrails.yaml` must never be modified without explicit human approval. This is the safety boundary for the entire agent system.
- **Three-layer prompt resolution.** Agent prompts load from (1) optimizer-promoted variants in `config/prompts/`, (2) canonical `.md` files in `agents/`, (3) hardcoded Python fallback. First hit wins. This enables A/B testing without code changes.
- **Evaluator routing is domain-specific.** The judge dispatches evaluation to domain-specific evaluators based on content type (written-content-judge, visual-content-judge, brand-safety-judge). Generic "is this good?" evaluation is an anti-pattern.
- **Intelligence over cost.** Every agent runs on the highest-capability model appropriate for its task. Claude Opus for strategy, Sonnet for content generation. The Mac Mini runs infrastructure, not inference.

## Production Environment

- **Hardware:** Mac Mini (infrastructure only — databases, orchestration, memory systems)
- **Intelligence:** Claude Opus (strategy decisions), Claude Sonnet (content generation, evaluation)
- **Agent framework:** ReAct loop, episodic execution (weekly trigger via cron or Telegram)
- **Silo communication:** MCP (Model Context Protocol) tool calls to genpeli, pilaster, social-media-automatization
- **Observability:** Langfuse tracing (tokens, cost, latency, scores), Observatory dashboard (FastAPI + Next.js)
- **State:** File-based — `trajectory.jsonl`, `AGENTS.yaml`, `eval_history.jsonl`, `MEMORY.md`
- **Cost target:** Full operation under $500/month

## Known Anti-Patterns

- **Storing analytics in Holus:** Analytics data belongs in social-media-automatization. Holus reads it via MCP, never persists it. Duplicating data creates staleness and consistency bugs.
- **Calling silo APIs directly instead of via MCP:** The MCP boundary is the contract. Direct API calls bypass the tool abstraction and break when silo APIs change.
- **Generic quality evaluation:** Using a single "rate this 1-10" prompt instead of domain-specific evaluators (hook quality, CTA effectiveness, brand safety) produces meaningless scores that cannot drive improvement.
- **Building Phase 2 before Phase 1 works:** The build order is strict. Phase 1 (one working loop) must produce content the founder is proud of before automating (Phase 2) or optimizing (Phase 3).
- **Adding execution capabilities to Holus:** Video editing, image generation, or direct publishing in Holus code violates the federated architecture. Holus briefs, silos execute.
- **Editing optimizer-generated prompt variants by hand:** `config/prompts/` is written exclusively by the prompt optimizer. Manual edits here corrupt the A/B testing pipeline.

## Glossary

- **Silo:** An independent repo that owns its own data and execution. Holus communicates with silos exclusively via MCP tool calls.
- **MCP:** Model Context Protocol. The tool-calling standard for AI agents. Each silo exposes its capabilities as MCP tools.
- **ReAct loop:** Observe → Reason → Act → Evaluate. The agent execution pattern Holus follows each cycle.
- **trajectory.jsonl:** Append-only log of every decision Holus makes — what was decided, why, and the evaluation score. The memory that makes learning possible.
- **AGENTS.yaml:** Single source of truth for all 32 agents: name, model, role, input/output contract, and evaluation rubric.
- **Observatory:** FastAPI + Next.js dashboard that reads from file-based state to surface agent status, decisions, evaluations, and costs. Dual-purpose: operations and portfolio artifact.
- **JudgeAgent:** Evaluates every content piece using domain-specific rubrics. Routes to specialized evaluators (written-content-judge, visual-content-judge, brand-safety-judge).
- **Prompt optimizer:** A/B tests prompt variants. Variant A ships to 50% of runs, variant B to the other 50%. After 20+ samples, the winner becomes the new baseline.
- **Reflexion:** Verbal reinforcement learning — after each cycle, the agent reads its own trajectory and writes a reflection that seeds the next cycle's reasoning.
- **Kill switch:** Global pause mechanism in `core/kill_switch.py` for when something goes wrong. Stops all agent execution immediately.
