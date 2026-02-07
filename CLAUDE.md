# Holus

Personal AI Agent Workforce for local-first automation.

## The Vision

Deploy specialized AI agents on local machine for 24/7 personal assistance.

## Commands

- Dev: `python -m holus.main`
- Test: `python -m pytest tests/`
- Lint: `flake8 core/ agents/ tools/`
- Build: `No build step (runtime Python app)`

## Structure

- Pages: `dashboard/templates/`
- Components: `agents/`
- Lib: `core/`
- Server: `dashboard/`
- Tests: `tests/`

## Agents

Load from `.ai/agents/`:

- builder.md (features, bugs, tests, review)
- operator.md (deploy, security, infrastructure)
- communicator.md (docs, UI, support)
- strategist.md (prioritization, feedback, growth)

## Standards

- `.ai/standards/code/` (Python, Python + LangChain/LangGraph, testing)
- `.ai/standards/api/design.md`
- `.ai/standards/security/baseline.md`
- `.ai/standards/comms/voice.md`

## Critical Rules

- Agents must not conflict on shared resources\n- Keep human-in-the-loop for high-stakes actions\n- Preserve agent memory integrity

## Key Files

- `core/orchestrator.py`\n- `core/base_agent.py`\n- `agents/inbox_manager/agent.py`

## Database Tables

- ChromaDB collections per agent

## External Services

- Telegram Bot API\n- Gmail API\n- GitHub API\n- Trading APIs

## Current Focus

See `.ai/contexts/current-priorities.md`

## Two Parallel Systems

| System | Location | Purpose |
|--------|----------|---------|
| **Playbooks** | `docs/playbooks/` | Human-facing prompts for driving AI sessions |
| **.ai** | `.ai/` | AI-facing context and standards for autonomous operation |

Use **playbooks** when you want to guide an AI through a specific workflow step-by-step.
Use **.ai** when you want AI to operate autonomously with full context.

## Development Workflow

Phase-based playbook in `docs/playbooks/`:

1. `1-spec-create.md` - Write detailed specs from ideas
2. `2-spec-review.md` - QA specs before implementation
3. `3-implement.md` - Build from specs
4. `4-audit-logic.md` - Hostile bug hunting (be adversarial)
5. `5-audit-intent.md` - UX and intent verification
6. `6-fix-iterate.md` - Apply fixes with minimal changes

Usage: "Read docs/playbooks/4-audit-logic.md and audit the feature I just built"

## MCP Servers

Configured in `.mcp.json` - filesystem, memory, GitHub access.

## Project Overrides

- Pre-merge CLAUDE notes (if present):
- none
- Use repository READMEs and docs for feature-level constraints before implementation.
