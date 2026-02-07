# AGENTS.md - Holus Project Constitution

## Project Overview

Holus is **Personal AI Agent Workforce for local-first automation.**.

**Vision:** Deploy specialized AI agents on local machine for 24/7 personal assistance.

## Build Phases

| Phase | Timeline | Focus |
|-------|----------|-------|
| **MVP** | 0-8 weeks | Core orchestrator, base agent framework, and one agent (Inbox Manager) |
| **V1.5** | 8-16 weeks | Add remaining agents: Job Hunter, Trading Monitor, Social Media, Research Scout |
| **V2** | 16+ weeks | Multi-environment hardening and operational maturity |

## Quick Commands

| Command | Purpose |
|---------|---------|
| `pip install -r requirements.txt` | Install dependencies |
| `python -m holus.main` | Start dev server |
| `No build step (runtime Python app)` | Production build |
| `python -m pytest tests/` | Run tests |
| `flake8 core/ agents/ tools/` | Lint and auto-fix |

## Tech Stack

- **Framework:** Python + LangChain/LangGraph
- **Language:** Python
- **Database:** ChromaDB
- **Agent orchestration, scheduled tasks, memory store, notifications**

## Project Structure

```
holus/
├── core agents tools/           # Source code
├── agents/       # Reusable components
├── core/              # Utilities and libraries
├── dashboard/           # API routes and server logic
└── tests/            # Test files
```

## Two Parallel Systems

| System | Location | Purpose |
|--------|----------|---------|
| **Playbooks** | `docs/playbooks/` | Human-facing prompts for driving AI sessions |
| **.ai** | `.ai/` | AI-facing context and standards for autonomous operation |

Use **playbooks** when you want to guide an AI through a specific workflow step-by-step.
Use **.ai** when you want AI to operate autonomously with full context.

## Agent System

| Task Type | Agent | File |
|-----------|-------|------|
| Build anything technical | Builder | `.ai/agents/builder.md` |
| Keep it running | Operator | `.ai/agents/operator.md` |
| Talk to humans | Communicator | `.ai/agents/communicator.md` |
| Decide what to build | Strategist | `.ai/agents/strategist.md` |

## Standards

- Python: `.ai/standards/code/python.md`
- Python + LangChain/LangGraph: `.ai/standards/code/langchain.md`
- Testing: `.ai/standards/code/testing.md`
- API: `.ai/standards/api/design.md`
- Security: `.ai/standards/security/baseline.md`
- Voice: `.ai/standards/comms/voice.md`

## Workflows

- Ship Feature: `.ai/workflows/ship-feature.md`
- Investigate Bug: `.ai/workflows/investigate-bug.md`
- Customer Feedback: `.ai/workflows/customer-feedback.md`
- Weekly Ops: `.ai/workflows/weekly-ops.md`

## Contexts

- Product: `.ai/contexts/product-context.md`
- Priorities: `.ai/contexts/current-priorities.md`
- Optional project-specific context: `.ai/contexts/holus.md`

## Templates

- PR Description: `.ai/templates/pr-description.md`
- Changelog Entry: `.ai/templates/changelog-entry.md`
- Customer Response: `.ai/templates/customer-response.md`
- Weekly Update: `.ai/templates/weekly-update.md`

## Core Rules

### Always

- Use Python strict mode
- Write tests for business logic
- Run `flake8 core/ agents/ tools/` before committing
- Add documentation to exported functions
- Keep docs, specs, and context files aligned with shipped code

### Ask First

- Adding new dependencies
- Modifying database schema
- Changing authentication flow
- Major architectural changes
- Changes to production credentials, billing, or automation schedules

### Never

- Commit API keys or secrets
- Disable type checking
- Skip error handling
- Never bypass auth, rate limits, or audit logging controls

## Escalation (All Agents)

- Work estimate > 1 day
- Breaking change to API or database
- Security severity > Medium
- Confidence is low

See `.ai/decision-boundaries.md` for full authority matrix.

## Domain Concepts

- Agent specialization\n- Task scheduling\n- Memory persistence\n- Notification routing

## Specs

- **MVP:** `specs/holus-core.md`

## Project Overrides

- Pre-merge AGENTS (if present):
- none
- Project-specific context source: `.ai/contexts/holus.md`
- Existing repository docs remain authoritative for business/domain details.
