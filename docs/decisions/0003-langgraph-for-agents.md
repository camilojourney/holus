# ADR-0003: LangGraph as Agent Orchestration Framework

## Status

Accepted

## Context

Each Holus agent needs an orchestration framework to manage multi-step reasoning workflows -- the sequence of tool calls, conditional routing, state management, and checkpointing that turns a raw LLM call into a reliable agent. The major options:

| Framework | Production Usage | Strengths | Weaknesses |
|-----------|-----------------|-----------|------------|
| **LangGraph** | Replit, LinkedIn, Uber, 400+ companies | Best latency/token efficiency in benchmarks; native graph-based execution; built-in human-in-the-loop; persistent checkpointing | Steeper learning curve than CrewAI |
| **CrewAI** | Fast prototyping, small teams | Fastest time-to-demo; role-based agent definition is intuitive | Teams consistently report hitting ceilings at 6-12 months and migrating to LangGraph |
| **AutoGen (Microsoft)** | Research, multi-agent conversation | Good for agent-to-agent chat patterns | Conversation-centric model does not map to Holus's event-driven architecture |
| **Raw Anthropic API** | Maximum flexibility | Zero framework overhead; Anthropic's own recommended patterns | Must build state management, checkpointing, tool routing, and error handling from scratch |
| **Anthropic Orchestrator-Worker** | Anthropic's recommended pattern | Clean separation of concerns | LangGraph formalizes exactly this pattern with built-in tooling |

The critical requirements for Holus:

1. **Human-in-the-loop interruptions:** The trading agent must pause for human approval on trades >$500. Non-negotiable.
2. **Persistent checkpointing:** Long-running tasks (trading workflow lifecycle, content pipeline) must survive agent crashes and replay from exact failure points.
3. **Multi-model routing per node:** Different nodes in the same graph use different models (Opus for risk validation, Sonnet for signal generation).
4. **Supervisor pattern:** A coordinator node delegates to specialized subgraphs -- native to the Phase 3 Holus Coordinator.
5. **Self-hosted deployment:** LangGraph Platform runs via Docker on the Mac Mini, managing agent lifecycle without cloud dependencies.

## Decision

**LangGraph** for all agent orchestration.

Each agent is a LangGraph `StateGraph` where nodes represent reasoning steps and edges represent conditional routing. The supervisor pattern -- a coordinator node that delegates to specialized subgraphs -- is native to LangGraph, enabling the Phase 3 Holus Coordinator without a framework migration.

Specific usage:

- **Trading agent:** StateGraph with SignalGenerator -> RiskManager -> ExecutionHandler nodes. Human-in-the-loop interrupt at RiskManager for trades >$500. Checkpointed at every state transition.
- **Content agent:** StateGraph with StrategyPlanner -> TextGenerator -> VisualGenerator -> VideoGenerator -> Distributor nodes. Conditional edges skip visual/video if content type is text-only.
- **Coding agent:** Primarily Claude Code CLI (not LangGraph), but the self-improvement loop (Manager -> CodeImprover -> Judge -> Optimizer) runs as a LangGraph workflow.
- **Pilaster agent:** StateGraph with WorkflowIntelligence -> ComfyUIExecution -> QualityAssessment -> MemoryUpdate nodes.
- **Holus Coordinator (Phase 3):** Supervisor StateGraph that reads events, synthesizes cross-project patterns, and publishes directives.

## Consequences

### Positive

- **No framework migration needed** between Phase 1 (independent agents) and Phase 3 (coordinator). Same framework scales from simple to complex.
- **Human-in-the-loop is first-class:** Built-in `interrupt_before` and `interrupt_after` for any node. Critical for trading safety.
- **Persistent checkpointing:** LangGraph's built-in checkpointer means trading workflows survive crashes and replay from the last successful node.
- **Native multi-model routing:** Each node specifies its own model. Risk validation always runs on Opus; signal evaluation runs on Sonnet.
- **LangGraph Platform (self-hosted via Docker):** Provides deployment runtime, agent lifecycle management, and API server on the Mac Mini.
- **First-class streaming:** Real-time observability into what each agent is doing at each node.

### Negative

- **Steeper learning curve** than CrewAI. The graph-based mental model requires understanding nodes, edges, conditional routing, and state reducers.
- **Framework lock-in:** Agent logic is expressed in LangGraph's graph DSL. Migrating away requires rewriting all workflows.
- **Overhead for simple tasks:** A 2-step agent (call LLM, use tool) does not need a full StateGraph. But consistency across all agents outweighs this.

### Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| LangGraph API breaking changes | Low | Pin versions in `pyproject.toml`; LangGraph follows semver |
| LangGraph Platform stability issues | Medium | Can fall back to running graphs directly via `graph.invoke()` without Platform |
| CrewAI surpasses LangGraph in capabilities | Very Low | LangGraph's production adoption (Replit, Uber, LinkedIn) provides strong ecosystem momentum |

## Alternatives Considered

### Alternative A: CrewAI

- Role-based agent definition, fast prototyping, lower learning curve
- Rejected because: Teams consistently report hitting ceilings at 6-12 months. Holus is a long-term system. Migrating from CrewAI to LangGraph mid-project would be more expensive than starting with LangGraph.

### Alternative B: Raw Anthropic API

- Maximum flexibility, zero framework overhead, uses Anthropic's own recommended patterns
- Rejected because: Must build state management, persistent checkpointing, human-in-the-loop interrupts, tool routing, and error handling from scratch. LangGraph provides all of this out of the box. The 2-4 weeks of custom development does not justify avoiding a well-maintained framework.

### Alternative C: AutoGen (Microsoft)

- Multi-agent conversation patterns, good for agent-to-agent chat
- Rejected because: AutoGen's conversation-centric model assumes agents talk to each other. Holus agents communicate through events, not conversations. The paradigm mismatch would require fighting the framework.

### Alternative D: Temporal.io for Everything

- Durable execution for all workflows, not just trading
- Decision: Use Temporal.io specifically for trading agent workflows (where durable execution and crash replay are non-negotiable for financial safety). Use LangGraph for all agent orchestration logic. They are complementary: LangGraph manages the reasoning graph; Temporal.io manages the durable execution lifecycle around the trading graph.

## References

- [AI_OS_Blueprint_Intelligence_First.md](../../AI_OS_Blueprint_Intelligence_First.md) -- Agent framework comparison
- [HOLUS-ARCHITECTURE-DECISIONS.md](../../HOLUS-ARCHITECTURE-DECISIONS.md) -- Section 4: Python project structure
- LangGraph documentation: graph-based agent orchestration
- Anthropic orchestrator-worker pattern: the pattern LangGraph formalizes

---

**Date:** 2026-02-24
**Author:** Camilo Martinez
