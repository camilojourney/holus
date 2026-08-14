# Docs -- Holus

Reference documentation for architecture decisions, operational playbooks, and strategic direction.

## Strategic

| File | Description |
|------|-------------|
| [vision.md](vision.md) | 5-year vision, scope boundaries, success metrics |
| [roadmap.md](roadmap.md) | Now/Next/Later/Never priorities |

## Architecture Decision Records (ADRs)

| # | Decision | Status |
|---|----------|--------|
| [0000](decisions/0000-template.md) | ADR template | -- |
| [0001](decisions/0001-federated-over-unified.md) | Federated architecture over unified orchestration | Accepted |
| [0002](decisions/0002-claude-first-intelligence.md) | Claude-first intelligence layer (no local LLMs for reasoning) | Accepted |
| [0003](decisions/0003-langgraph-for-agents.md) | LangGraph as agent orchestration framework | Accepted |

## Data Contracts

| File | Audience | Description |
|------|----------|-------------|
| [lineage.md](lineage.md) | Operators / Holusight consumers | Versioned, read-only provenance contract, export, validation, privacy, and recovery |

## Playbooks

| File | Audience | Description |
|------|----------|-------------|
| [playbooks/development.md](playbooks/development.md) | Developer | Local setup from zero to running |
| [playbooks/agent-session.md](playbooks/agent-session.md) | AI agents | What to check at startup, where to write outputs |
| [playbooks/deployment.md](playbooks/deployment.md) | Operator | How to deploy and monitor Holus in production |

---

**Last updated:** 2026-02-24
