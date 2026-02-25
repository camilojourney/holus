# Holus Architecture

A guided tour of the codebase. Covers WHY each component exists, how they connect, and what not to change without discussion. For implementation details, read the source and inline comments.

**Last updated:** 2026-02-24
**Update cadence:** Only on major structural changes.

---

## High-Level Architecture

Holus is a **federated multi-agent system** with process-isolated domain agents communicating through a shared Redis event bus. Each agent is an independent OS process with its own memory, execution graph, and failure boundary. A lightweight Coordinator agent synthesizes cross-project intelligence daily without real-time orchestration overhead.

```
                         HOLUS FEDERATED ARCHITECTURE

    +-----------------+  +-----------------+  +-----------------+  +-----------------+
    |  TRADING AGENT  |  |  CONTENT AGENT  |  |  CODING AGENT   |  | PILASTER AGENT  |
    |                 |  |                 |  |                 |  |                 |
    | Own process     |  | Own process     |  | Own process     |  | Own process     |
    | Own LangGraph   |  | Own LangGraph   |  | Own LangGraph   |  | Own LangGraph   |
    | Own Mem0 scope  |  | Own Mem0 scope  |  | Own Mem0 scope  |  | Own Mem0 scope  |
    | Temporal.io     |  | n8n triggers    |  | Claude Code CLI |  | ComfyUI API     |
    +--------+--------+  +--------+--------+  +--------+--------+  +--------+--------+
             |                     |                     |                     |
             | publish             | publish             | publish             | publish
             v                     v                     v                     v
    +===========================================================================+
    |                        REDIS PUB/SUB EVENT BUS                            |
    |                                                                           |
    |  Channels:                                                                |
    |    holus.trading.signals       holus.content.performance                  |
    |    holus.coding.deploys        holus.pilaster.workflows                   |
    |    holus.system.alerts         holus.coordinator.directives               |
    |                                                                           |
    |  Persistence: Redis Streams (rolling 10K events per channel)              |
    +===========================================================================+
             |                                                       |
             v                                                       v
    +-----------------+                                   +-----------------------+
    |    COORDINATOR  |                                   |   SHARED SERVICES     |
    |    (Phase 3)    |                                   |                       |
    |                 |                                   |  PostgreSQL + pgvector |
    | Daily synthesis |                                   |  Redis                |
    | Opus 4 model    |                                   |  Mem0 (self-hosted)   |
    | Cross-project   |                                   |  Langfuse             |
    | intelligence    |                                   |  n8n                  |
    | Cognee graph    |                                   |  Temporal.io          |
    +-----------------+                                   +-----------------------+
```

**Why federated, not unified:** The compound error problem. A 1% error rate per agent step compounds to 63% failure by step 100. Production systems (Replit, Vercel, Cognition/Devin) all converge on independent agents with bounded communication channels. Holus follows the same pattern: agents publish events but never read each other's state directly.

---

## Core (`src/holus/core/`)

The shared foundation that every agent depends on. This is infrastructure code, not business logic.

**Why it exists:** All agents need configuration loading, event publishing, process management, kill switch checks, and structured logging. Centralizing these avoids drift between agents.

**Key files:**
- `config.py` -- Layered configuration: `config/base.yaml` (defaults) + `config/{agent}.yaml` (overrides) + environment variables (secrets). Env vars always win.
- `event_bus.py` -- Redis pub/sub + Streams. Agents publish `HolusEvent` Pydantic models. Fire-and-forget publishing so events never block the publishing agent. Redis Streams persist events for coordinator replay.
- `process_manager.py` -- Supervisor pattern. Each agent launches as a subprocess with its own stdout/stderr logs. Crash handling with exponential backoff. Max 3 restarts before alerting the founder.
- `kill_switch.py` -- Three-level kill switch (per-agent, per-domain, global) backed by Redis keys. Every agent checks `kill_switch.is_active(self.agent_name)` before every action.
- `logging.py` -- Structured logging via structlog with Langfuse integration. Every log line includes `agent_name` for filtering.
- `models.py` -- Shared Pydantic models: `HolusEvent`, `AgentStatus`, `GuardrailViolation`.

**Do not change:** The `HolusEvent` schema without updating all agents and the coordinator's event consumer. The kill switch check-before-every-action pattern. The Pydantic validation on event publishing.

---

## Trading Agent (`src/holus/agents/trading/`)

Autonomous trading agent with a mandatory three-component pipeline enforcing structural separation between signal generation, risk validation, and execution.

**Why it exists:** Automate trading signal detection and execution with multiple layers of safety. The structural separation makes it physically impossible for a signal generation error to execute a trade without risk validation.

**Architecture:**
```
    SignalGenerator          RiskManager             ExecutionHandler
    (Sonnet 4.5)            (Opus 4 ALWAYS)         (Deterministic)
         |                       |                        |
    Market data, FinBERT    Guardrail DB,            Alpaca API
    News feeds, TA          Portfolio state,          (ONLY here)
    indicators              Risk metrics              Order mgmt
         |                       |                        |
    NO broker API           Human-in-loop             No AI reasoning.
    access. Ever.           for >$500 trades          Pure execution.
         |                       |                        |
         +----------> validate ----------> execute ------->|
                                                          |
                    TEMPORAL.IO WORKFLOW                   |
                    (durable execution, crash replay)      |
                                                          v
                    TRADE MEMORY PROTOCOL
                    L1: Working (every trade + context)
                    L2: Episodic (extracted patterns, weekly)
                    L3: Semantic (general principles, monthly)
```

**Key files:**
- `agent.py` -- `TradingAgent(BaseAgent)` main class
- `signal_generator.py` -- Signal detection. NO broker API access.
- `risk_manager.py` -- Guardrail validation. ALWAYS runs on Opus 4.
- `execution_handler.py` -- Alpaca API access. No AI reasoning. Defense-in-depth guardrail re-check.
- `memory.py` -- Three-tier TradeMemory protocol (L1/L2/L3)
- `workflows.py` -- Temporal.io workflow definitions for durable trade lifecycle

**Do not change:** The three-component air gap between signal generation and execution. The requirement that RiskManager always uses Opus 4. The defense-in-depth guardrail check in ExecutionHandler. Paper-to-live graduation criteria in `config/trading_agent.yaml`.

---

## Content Agent (`src/holus/agents/content/`)

n8n-orchestrated four-stage content pipeline: Strategy -> Generation (text/visual/video) -> Distribution -> Performance feedback.

**Why it exists:** Automate content creation and multi-platform distribution while building a feedback loop that improves content strategy over time.

**Key files:**
- `agent.py` -- `ContentAgent(BaseAgent)` main class
- `strategy.py` -- Content strategy planner. Opus 4 runs monthly to analyze performance and set content calendar.
- `text_gen.py` -- Article and social post generation. Sonnet 4.5 for volume with aggressive prompt caching.
- `visual_gen.py` -- Image generation routing: ComfyUI (local prototyping) vs Replicate/fal.ai (production batches at $0.003/image).
- `video_gen.py` -- Kling AI + ElevenLabs voiceover + Creatomate template assembly.
- `distribution.py` -- Late API client for 13-platform publishing.
- `feedback.py` -- Performance tracking. Stores topic/platform/timing/format effectiveness in Mem0.

**Do not change:** The intelligence routing (Opus for strategy, Sonnet for generation). The Late API as the single distribution endpoint. The feedback loop storage format in Mem0.

---

## Coding Agent (`src/holus/agents/coding/`)

Claude Code CLI as the primary interface, with GitHub Actions for automation and a self-improvement loop.

**Why it exists:** Accelerate development velocity across all repos. Automated PR review, weekly self-improvement cycles, cross-repo dependency management.

**Key files:**
- `agent.py` -- `CodingAgent(BaseAgent)` main class
- `cross_repo.py` -- Cross-repo dependency management. Checks version divergence, propagates security patches, syncs shared Pydantic types.
- `self_improve.py` -- Self-improvement loop: Manager -> Code Improver -> Judge -> Prompt Optimizer.
- `github_actions.py` -- GitHub Actions integration for automated PR review and scheduled maintenance.

**Do not change:** The Claude Code CLAUDE.md file as the project memory contract. The self-improvement loop ordering (Manager reads trajectory -> sets priorities -> Code Improver executes ONE task -> Judge scores).

---

## Pilaster Agent (`src/holus/agents/pilaster/`)

ComfyUI workflow intelligence: version control, optimization, quality assessment, and config-to-outcome learning.

**Why it exists:** Manage ComfyUI image generation pipelines with AI-driven workflow optimization. Version-control node graphs, assess output quality via Claude Vision, and build a recommendation engine for workflow parameters.

**Key files:**
- `agent.py` -- `PilasterAgent(BaseAgent)` main class
- `workflow_versioning.py` -- Hash-based dedup, workflow diffing (added/removed/modified nodes), version history.
- `quality_assessment.py` -- Claude Vision image quality scoring: technical quality, prompt adherence, aesthetic quality, commercial viability. Pass threshold: overall >= 7/10.
- `routing.py` -- Routes generation between local ComfyUI (Metal GPU, prototyping) and Replicate API (Flux Schnell, production batches).

**Do not change:** The quality assessment scoring schema (downstream memory depends on consistent format). The workflow JSON version format.

---

## Coordinator Agent (`src/holus/agents/coordinator/`)

**Phase 3 component.** Lightweight daily intelligence synthesis, NOT real-time orchestration.

**Why it exists:** Identify cross-project optimization opportunities that no single agent can see. Example: content engagement on trading topics correlates with signal accuracy. The Coordinator discovers these patterns and publishes advisory directives.

**Critical design constraint:** The Coordinator is advisory only. It publishes recommendations to `holus.coordinator.directives`. Domain agents may subscribe but are not required to act on directives. The Coordinator NEVER directly controls any agent's execution.

**Key files:**
- `agent.py` -- `HolusCoordinator(BaseAgent)` main class
- `synthesis.py` -- Daily cross-project synthesis. Reads last 24h of Redis Streams + latest agent reports. Runs on Opus 4.
- `knowledge_graph.py` -- Cognee integration for cross-project relationship storage and traversal.
- `reporting.py` -- Daily and weekly summary reports for the founder.

**Event consumption priority:**
- **High:** `market_regime_shift`, `risk_alert`, `daily_pnl`, `agent_crash`, `guardrail_violation`
- **Medium:** `engagement_update`, `topic_trending`, `pr_merged`, `ci_failure`, `workflow_optimized`
- **Ignored:** `signal_generated` (too granular), `content_published` (routine)

**Do not change:** The advisory-only constraint. The daily (not real-time) execution cadence. Making this real-time reintroduces the compound error problem the federated architecture was designed to avoid.

---

## Memory (`src/holus/memory/`)

Agent memory infrastructure. Every agent gets an isolated memory scope.

**Why it exists:** Agents need to accumulate knowledge across sessions without corrupting each other's context. Memory isolation is a load-bearing architectural constraint.

**Key files:**
- `mem0_client.py` -- Mem0 self-hosted client. Enforces memory isolation: each agent can only read/write its own `agent_id` scope. User-level memory (founder preferences) is shared read-only.
- `pgvector_client.py` -- pgvector for document-level RAG. Workflow documentation, market research, codebase context. Zero-latency local retrieval.
- `trajectory.py` -- Manages `.self-improvement/memory/trajectory.jsonl`. Append-only. Records every agent run with timestamp, actions, outcome, cost.

**Do not change:** The memory isolation enforcement in `mem0_client.py`. The trajectory append-only contract. The `agent_id` scoping mechanism.

---

## Observability (`src/holus/observability/`)

Tracing, metrics, and alerting.

**Why it exists:** Langfuse traces every agent run (tool calls, reasoning steps, outcomes). This data fuels the self-improvement loop: monthly DSPy optimization uses Langfuse traces as training data.

**Key files:**
- `langfuse_client.py` -- Langfuse tracing integration. Every LLM call, tool invocation, and agent decision is traced.
- `metrics.py` -- Prometheus-compatible metrics for infrastructure monitoring.
- `alerts.py` -- Alert routing to Slack and email. Triggered by: agent crashes, guardrail violations, circuit breaker activations, daily P&L thresholds.

**Do not change:** The Langfuse trace structure (DSPy optimization depends on consistent trace schemas).

---

## Self-Improvement (`src/holus/self_improvement/`)

The learning loop that makes the system get better over time.

**Why it exists:** Three production-ready techniques for improving agent performance without model fine-tuning:

1. **DSPy MIPROv2** (`dspy_optimizer.py`) -- Bayesian optimization over prompts and few-shot examples. Requires 30+ labeled examples. Costs $2-10 per optimization run. Typically improves accuracy by 15-30%.
2. **Reflexion** (`reflexion.py`) -- Agents verbally reflect on failures, store reflections in Mem0 episodic memory, and improve future attempts. Zero infrastructure cost. Achieved 91% pass@1 on HumanEval vs GPT-4's 80%.
3. **TextGrad** (`textgrad.py`) -- Treats prompts as differentiable variables. LLM-generated textual gradients iteratively optimize outputs. Complementary to DSPy: TextGrad for test-time refinement, DSPy for pipeline optimization.

**Key files:**
- `dspy_optimizer.py` -- Monthly DSPy MIPROv2 optimization using Langfuse traces as training data.
- `reflexion.py` -- Per-agent reflection loops after failures.
- `textgrad.py` -- Test-time output refinement.
- `judge.py` -- Judge Agent scoring logic. Evaluates improvement quality.

**Do not change:** The monthly DSPy cadence (more frequent risks overfitting to recent data). The Judge Agent's independence from the Code Improver (the judge must not be influenced by the agent it evaluates).

---

## Integrations (`src/holus/integrations/`)

External service clients. Each integration is isolated in its own subpackage.

| Integration | Subpackage | Used By | Purpose |
|-------------|-----------|---------|---------|
| Anthropic Claude API | `claude_api/` | All agents | LLM reasoning with prompt caching + Batch API |
| Alpaca Trading API | `alpaca/` | Trading agent ONLY | Broker access, market data (SIP via Algo Trader Plus) |
| ComfyUI | `comfyui/` | Pilaster agent | Local image generation via REST + WebSocket API |
| Late API | `late_api/` | Content agent | 13-platform content distribution |
| n8n | `n8n/` | Content agent, all agents | Workflow automation webhook triggers |
| FinBERT | `finbert/` | Trading agent | Local financial sentiment analysis (~440MB, CPU, <100ms/headline) |

**Key design pattern in `claude_api/`:**
- `client.py` -- Anthropic API wrapper with automatic prompt caching
- `prompt_cache.py` -- Stable prefix (system prompt + tools + persistent memory) cached. Dynamic suffix (task + live data) not cached. 90% discount on cached reads.
- `batch.py` -- Batch API (50% discount) for non-time-sensitive operations: content drafts, weekly reports, optimization runs.
- `routing.py` -- Opus vs Sonnet routing. Decision rule: use Opus when the decision matters (risk eval, architecture, synthesis), Sonnet when volume is the constraint (content generation, routine review).

---

## Data Flow: How Information Moves Through the System

```
1. TRIGGER
   Schedule (n8n cron) / Webhook / Manual CLI command
        |
        v
2. AGENT ACTIVATION
   ProcessManager starts agent subprocess
   Agent checks KillSwitch -> if active, exit immediately
   Agent loads config (YAML + env vars)
   Agent connects to Mem0 (own scope only)
        |
        v
3. EXECUTION
   LangGraph StateGraph executes reasoning nodes
   Each node: LLM call (Opus/Sonnet) + tool invocations
   All calls traced to Langfuse
   Trading: wrapped in Temporal.io durable workflow
        |
        v
4. OUTPUT
   Agent produces result (trade, content, PR review, workflow optimization)
   Agent publishes HolusEvent to Redis event bus
   Agent updates own Mem0 memory
   Agent writes report to .self-improvement/reports/
   Run logged to trajectory.jsonl
        |
        v
5. CROSS-PROJECT (Phase 3)
   Coordinator reads Redis Streams (last 24h) + agent reports
   Opus 4 synthesizes cross-project patterns
   Publishes advisory directives to holus.coordinator.directives
   Updates Cognee knowledge graph
        |
        v
6. LEARNING LOOP
   Weekly: Manager extracts patterns from trajectory -> updates NEXT.md
   Weekly: Code Improver executes one task from NEXT.md
   Monthly: DSPy optimizes prompts from Langfuse traces
   Monthly: Security Sentinel audits all repos
```

---

## Infrastructure (`infrastructure/`)

Docker Compose configuration for all shared services.

**Services:**
- PostgreSQL 16 + pgvector extension (port 5432)
- Redis 7 with persistence (port 6379)
- Langfuse (port 3000)
- n8n (port 5678)
- Temporal.io server + UI (ports 7233, 8233)

**Runtime:** OrbStack on Mac Mini M4. All services start automatically on boot. Memory budget: ~16GB total.

**Key files:**
- `docker-compose.yml` -- Base service definitions
- `docker-compose.prod.yml` -- Production overrides
- `Dockerfile` -- Holus agent image
- `scripts/setup.sh` -- First-time infrastructure setup
- `scripts/backup.sh` -- Daily backup to cloud storage
- `scripts/health_check.sh` -- Service health verification

---

## Configuration (`config/`)

YAML for agent-specific configuration. Environment variables for secrets.

| File | Purpose | Change Frequency |
|------|---------|-----------------|
| `base.yaml` | Shared defaults: logging, Redis URL, Postgres URL | Rarely |
| `trading_agent.yaml` | Position limits, graduation criteria, risk thresholds | Ask First |
| `content_agent.yaml` | Feedback loop schedules, metrics tracked, platform config | Quarterly |
| `coding_agent.yaml` | Repo registry, self-improvement schedule | Quarterly |
| `pilaster_agent.yaml` | Quality thresholds, routing rules (local vs Replicate) | Quarterly |
| `coordinator.yaml` | Event consumption priority, synthesis schedule | Quarterly |
| `events.yaml` | Event bus channel + event type schema registry | Ask First |
| `guardrails.yaml` | Authority matrix, per-agent permission boundaries | NEVER without human approval |

---

## Load-Bearing Walls

These are architectural constraints that should NOT be changed without explicit discussion:

1. **Process isolation between agents.** Each agent is a separate OS process. No shared memory, no direct function calls between agents. Communication is event-based only.

2. **Memory scope isolation.** Each agent's Mem0 `agent_id` scope is private. No agent reads another agent's memory. Enforced in `src/holus/memory/mem0_client.py`.

3. **Trading three-component air gap.** SignalGenerator -> RiskManager -> ExecutionHandler. Only ExecutionHandler has Alpaca API access. RiskManager always runs Opus 4. No shortcuts.

4. **Kill switch check before every action.** Every agent's action loop includes `if kill_switch.is_active(self.agent_name): return`. Three levels: per-agent, per-domain, global.

5. **Coordinator is advisory only.** The Coordinator publishes recommendations, never commands. Domain agents retain full autonomy. The system must degrade gracefully to Phase 2 (independent agents) if the Coordinator is disabled.

6. **Event schema validation.** All events are Pydantic-validated `HolusEvent` models. The schema registry in `config/events.yaml` is the source of truth. Schema changes require updating all publishers and consumers.

7. **Guardrails configuration.** `config/guardrails.yaml` codifies the authority matrix. Changes require explicit human approval and are logged to the audit trail.

---

## Source Directory Map

```
src/holus/
    __init__.py
    __main__.py               # CLI entrypoint: python -m holus
    core/                     # Shared infrastructure (config, events, process mgmt, kill switch)
    agents/
        base.py               # BaseAgent abstract class
        trading/              # Trading agent (signal, risk, execution, memory, Temporal)
        content/              # Content agent (strategy, text, visual, video, distribution)
        coding/               # Coding agent (cross-repo, self-improve, GitHub Actions)
        pilaster/             # Pilaster agent (ComfyUI workflows, quality, versioning)
        coordinator/          # Coordinator agent (synthesis, Cognee graph, reporting)
    integrations/
        alpaca/               # Alpaca Trading API (broker + market data)
        claude_api/           # Anthropic API (caching, batch, model routing)
        comfyui/              # ComfyUI REST + WebSocket API
        late_api/             # Late API (13-platform distribution)
        n8n/                  # n8n webhook triggers
        finbert/              # FinBERT local sentiment analysis
    memory/                   # Mem0 client, pgvector client, trajectory management
    observability/            # Langfuse tracing, Prometheus metrics, alerting
    self_improvement/         # DSPy optimizer, Reflexion, TextGrad, Judge
```
