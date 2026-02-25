# ADR-0001: Federated Architecture Over Unified Orchestration

## Status

Accepted

## Context

Holus manages four autonomous agent domains (trading, content, coding, Pilaster) for a solo founder. The fundamental architectural question is how these agents relate to each other:

- **Approach A (Isolated):** Each agent is completely independent. No shared state, no communication. Simple to build and debug, but no cross-project learning. The trading agent cannot learn from content engagement patterns; the coding agent cannot leverage workflow insights from Pilaster.

- **Approach B (Unified):** A central orchestrator manages all agents, sharing state, routing tasks, and coordinating actions in real-time. Maximum cross-project intelligence, but creates a single point of failure across all revenue-generating projects, quadratic debugging complexity, and months of orchestration engineering before any agent ships.

The compound error problem is the single most important constraint. A 1% error rate per step compounds to 63% failure by step 100. Every production multi-agent system studied converges on the same lesson: independent agents with bounded communication channels.

| System | Architecture | Key Lesson |
|--------|-------------|------------|
| Vercel AI Gateway | Identical agent configs, centralized gateway, no shared state | Shared infrastructure, isolated intelligence |
| Replit Agent | Migrated from single-agent to multi-agent after error rates grew unmanageable | Single-agent complexity has a ceiling |
| Cognition/Devin | Full sandboxed environment per task | Process-level isolation is non-negotiable |
| Anthropic Multi-Agent Research | Independent subagents with lightweight artifact references | Context sharing causes more problems than it solves |

## Decision

**Federated Process Isolation with Shared Event Bus.**

Each agent runs as an independent OS process with its own LangGraph state machine, its own Mem0 memory scope, and its own error boundary. Agents communicate exclusively through a Redis pub/sub event bus -- they publish domain events but never read another agent's state directly.

The architecture phases in cross-project learning gradually:

1. **Phase 1:** Independent agents, shared infrastructure (PostgreSQL, Redis, Langfuse). Zero cross-agent communication.
2. **Phase 2:** Shared event bus. Agents publish significant events (market regime shifts, engagement metrics, CI failures). Any agent can subscribe, but subscriptions are advisory.
3. **Phase 3:** Lightweight Holus Coordinator agent. A daily Opus 4 synthesis that reads cross-project events, identifies optimization opportunities, and publishes advisory directives. Not real-time orchestration.

## Consequences

### Positive

- **Fault isolation:** Trading agent crashing at 3 AM does not take down the content pipeline
- **Independent deployment:** Each agent can be built, tested, and iterated without risking others
- **Low cognitive load:** Solo founder can understand and debug each agent independently
- **Days to first working agent:** Start shipping immediately with Phase 1
- **Graceful degradation:** If Phase 3 proves too complex, the system degrades cleanly to Phase 2 with no rewrite

### Negative

- **No cross-project learning in Phase 1:** Agents are blind to each other's patterns until the event bus is added
- **Eventual consistency:** Cross-project insights arrive daily (via coordinator), not in real-time
- **Duplication:** Some shared logic (Claude API client, config loading) must be careful not to diverge across agents

### Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Redis (event bus) is a single point of failure | Medium | Redis Sentinel for failover; agents continue operating without events |
| Event schema drift between agents | Medium | Pydantic schema validation; schema registry in `config/events.yaml` |
| Coordinator makes bad cross-project recommendations | Medium | Recommendations are advisory; agents can ignore; founder reviews weekly |

## Alternatives Considered

### Alternative A: Fully Isolated (Approach A)

- Each agent is completely independent, no event bus, no coordinator
- Rejected because it permanently prevents cross-project learning, which is the core value proposition of Holus. The trading agent discovering that content engagement correlates with certain market conditions is genuinely valuable.

### Alternative B: Unified Orchestration (Approach B)

- Central real-time orchestrator manages all agents, shared state, real-time routing
- Rejected because it creates a single point of failure, months of orchestration engineering before shipping, and compound error rates that grow quadratically with agent count. Vercel and Replit both started here and migrated away.

## References

- [AI_OS_Blueprint_Intelligence_First.md](../../AI_OS_Blueprint_Intelligence_First.md) -- Original research
- [HOLUS-ARCHITECTURE-DECISIONS.md](../../HOLUS-ARCHITECTURE-DECISIONS.md) -- Section 1: Federated vs Unified
- Anthropic multi-agent research: independent subagents with artifact references
- Replit Agent migration: single-agent to multi-agent after error rates grew unmanageable

---

**Date:** 2026-02-24
**Author:** Camilo Martinez
