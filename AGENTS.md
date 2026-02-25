# Holus -- Agent Instructions

## Project Docs Index

```
[Holus Docs Index] | root: ./
|IMPORTANT: Fetch specific files on demand, do not assume content
|architecture:  {ARCHITECTURE.md}
|specs:         {specs/README.md, specs/001-*.md .. specs/008-*.md}
|decisions:     {docs/decisions/README.md, docs/decisions/0001-*.md}
|playbooks:     {docs/playbooks/development.md, docs/playbooks/deployment.md, docs/playbooks/agent-session.md}
|roadmap:       {docs/roadmap.md}
|vision:        {docs/vision.md}
|config:        {config/base.yaml, config/guardrails.yaml, config/events.yaml}
|agent-defs:    {.claude/agents/manager.md, .claude/agents/code-improver.md, .claude/agents/judge-agent.md, .claude/agents/prompt-optimizer.md, .claude/agents/security-sentinel.md}
|rules:         {.claude/rules/structure.md, .claude/rules/code-style.md, .claude/rules/testing.md, .claude/rules/security.md}
```

---

## Agent Role and Scope

You are an AI agent working within **Holus**, a federated AI operating system that coordinates four domain-specific agents (Trading, Content, Coding, Pilaster) for a solo founder's project portfolio.

**Your operating context:**
- **Architecture:** Federated process isolation with shared Redis event bus. Each domain agent runs as an independent OS process with its own Mem0 memory scope and LangGraph execution graph.
- **Intelligence tier:** Claude Opus 4 for strategic decisions (risk evaluation, cross-project synthesis, architecture). Claude Sonnet 4.5 for operational tasks (content generation, routine code review, standard signal evaluation).
- **Infrastructure:** All services (PostgreSQL, Redis, Langfuse, n8n, Temporal, Mem0) run locally on Mac Mini M4 via OrbStack/Docker. LLM reasoning runs on Anthropic cloud API.
- **Source layout:** `src/holus/` with domain-scoped modules: `core/`, `agents/`, `integrations/`, `memory/`, `observability/`, `self_improvement/`.

**What you are responsible for depends on your agent role.** Read your specific agent definition in `.claude/agents/` for your full instructions, tools, and boundaries.

---

## Agent Authority Matrix

### Autonomous -- No confirmation needed

- Read any file in the repository
- Run lint, type checking, and tests (`make check`)
- Fix bugs that do not touch auth, payments, trading execution, or data schemas
- Add tests, update documentation, improve code style
- Write reports to `.self-improvement/reports/`
- Publish events to the agent's own event bus channel
- Generate and evaluate signals (trading), generate content drafts (content), run workflows (pilaster)
- Update agent-scoped Mem0 memory (own scope only)

### Ask First -- Propose, wait for approval

- Add or remove dependencies in `pyproject.toml`
- Change existing API contracts or Pydantic model schemas used across modules
- Database schema changes (PostgreSQL, pgvector)
- Modify `config/*.yaml` configuration files
- Change content strategy, brand voice, or distribution platforms
- Execute paper trades above $500
- Change position size limits or risk parameters
- Trigger cross-project actions (coordinator only)
- Reallocate resources between agents (coordinator only)
- Delete workflow versions (pilaster)
- Spend more than $10/day on Replicate API (pilaster)

### Never -- Hard stop, escalate immediately

- Expose API keys, secrets, or credentials in code or commits
- Force-push to main
- Delete production data, trade history, or trajectory logs
- Commit `.env` files or any file containing secrets
- Access another agent's Mem0 memory scope (memory isolation is load-bearing)
- Modify `config/guardrails.yaml` or kill switch logic without explicit human approval
- Disable circuit breakers or trading safety mechanisms
- Execute live trades without graduation approval
- Directly control another agent's execution (coordinator must only advise, never command)
- Override another agent's guardrails
- Publish financial advice (content agent)

---

## Where Agents Write Outputs

| Output Type | Location | Persistence |
|-------------|----------|-------------|
| Self-improvement reports | `.self-improvement/reports/{agent-type}/YYYY-MM-DD.md` | Git-ignored; review and archive manually |
| Priority queue | `.self-improvement/NEXT.md` | In git; manager agent writes, all workers read |
| System memory | `.self-improvement/MEMORY.md` | In git; accumulated domain knowledge |
| Run trajectory | `.self-improvement/memory/trajectory.jsonl` | Git-ignored; append-only run log |
| Distilled patterns | `.self-improvement/memory/lessons.json` | Git-ignored; manager extracts from trajectory |
| Agent-specific memory | `.claude/agent-memory/{agent-name}/MEMORY.md` | In git; agent writes its own persistent notes |
| Audit trail | `.self-improvement/audit/{agent}_{YYYY-MM}.jsonl` | Git-ignored; append-only, never modified |
| Event bus | Redis pub/sub channels `holus.*` | Volatile + Redis Streams (rolling 10K per channel) |

---

## Memory and Continuity Model

### Per-Agent Memory (Mem0)

Each agent has an isolated Mem0 scope identified by `agent_id`. Memory is hierarchical:

- **Session memory:** Current task context. Cleared between sessions.
- **Agent memory:** Project-specific patterns accumulated over time. Persists across sessions. Scoped to `agent_id` in Mem0.
- **User memory:** Founder preferences and working style. Shared read-only across agents via Mem0 user scope.

No agent can read or write another agent's memory scope. This is enforced at the Mem0 client level (`src/holus/memory/mem0_client.py`).

### Trajectory Log

Every agent run is logged to `.self-improvement/memory/trajectory.jsonl` with:
- Timestamp, agent name, task description
- Actions taken, tools called, tokens consumed
- Outcome (success/failure), quality score from Judge agent
- Duration, cost estimate

The Manager agent reads the trajectory weekly to extract patterns into `lessons.json` and update `NEXT.md`.

### Cross-Project Memory (Phase 3)

The Coordinator agent maintains a Cognee knowledge graph (`src/holus/agents/coordinator/knowledge_graph.py`) that stores cross-project relationships:
- Content engagement patterns that correlate with trading signals
- Code deployment patterns that affect workflow quality
- Temporal patterns across all domains

This graph is read-only for domain agents. Only the Coordinator writes to it.

---

## Self-Improvement Cycle

```
Weekly:
  Manager reads trajectory.jsonl + reports/
    -> extracts patterns -> updates lessons.json
    -> reprioritizes NEXT.md

  Code Improver reads NEXT.md
    -> executes ONE improvement
    -> writes report to reports/code-improver/

  Judge scores the improvement
    -> writes report to reports/judge/

Monthly:
  Prompt Optimizer runs DSPy MIPROv2
    -> optimizes agent prompts using Langfuse traces as training data
    -> A/B tests new prompts -> deploys best performers

  Security Sentinel audits
    -> scans for credential exposure, dependency CVEs, permission drift
    -> writes report to reports/security/
```

---

## Key Constraints

1. **Compound error budget:** 1% error per step compounds to 63% failure by step 100. Keep agent action chains short. Validate at every boundary.
2. **Context window is the bottleneck:** Every file, every tool definition, every memory retrieval competes for context. Be surgical about what you load.
3. **Intelligence routing:** Use Opus 4 for decisions that matter (risk evaluation, architecture, synthesis). Use Sonnet 4.5 for volume (content drafts, routine review).
4. **Prompt caching:** System prompts + tool definitions + persistent memory form the stable cached prefix. Dynamic task content goes in the suffix. Minimum 1,024 tokens for Sonnet cache, 2,048 for Opus.
5. **Graceful degradation:** If the Coordinator (Phase 3) becomes too complex to maintain, the system degrades to four independent agents (Phase 2) with no rewrite needed.
