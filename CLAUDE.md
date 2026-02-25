# Holus

Federated AI Operating System for multi-project management.

## Commands

```bash
# Install
uv sync --all-extras

# Run
python -m holus                        # Start coordinator
python -m holus agent start trading    # Start single agent
python -m holus agent start --all      # Start all agents

# Test
pytest tests/ -x -v                    # All tests
pytest tests/unit/ -x -v               # Unit only
pytest tests/integration/ -x -v        # Integration only (requires Docker services)

# Lint + Type Check
ruff check src/ tests/                 # Lint
ruff format src/ tests/ --check        # Format check
mypy src/                              # Type check

# All checks (run before committing)
make check                             # Runs: ruff check + ruff format --check + mypy + pytest
```

## IMPORTANT Rules

- NEVER expose API keys, secrets, or credentials in code or commits. All secrets flow through environment variables via `.env` (never committed). See `.env.example` for the template.
- ALWAYS run `make check` before committing. Tests must pass, types must check, lint must be clean.
- NEVER modify `config/guardrails.yaml` or kill switch logic without explicit human approval. These are safety-critical components.
- NEVER allow any agent direct access to another agent's Mem0 scope. Memory isolation is a load-bearing architectural constraint.
- ALWAYS use Pydantic models for data crossing module boundaries. No raw dicts at API surfaces.

## Required Environment Variables

See `.env.example` for the full list. Critical:
- `ANTHROPIC_API_KEY` -- required for all agents
- `REDIS_URL` -- event bus (default: `redis://localhost:6379`)
- `DATABASE_URL` -- PostgreSQL + pgvector (default: `postgresql://holus:holus@localhost:5432/holus`)

## Context

- System design: @ARCHITECTURE.md
- Code style + testing + security: @.claude/rules/
- Decisions log: @docs/decisions/
- Specs index: @specs/README.md
- Agent authority matrix: @AGENTS.md
- Env template: @.env.example

## Tech Stack

- Python 3.12+ / uv / src-layout
- LangGraph (agent orchestration) + Anthropic Claude API (Opus 4 strategic, Sonnet 4.5 operational)
- Redis (event bus) + PostgreSQL/pgvector (storage) + Mem0 (agent memory)
- Langfuse (observability) + Temporal.io (durable execution for trading)
- n8n (workflow automation) + Docker/OrbStack (infrastructure)
