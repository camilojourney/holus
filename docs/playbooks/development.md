# Playbook: Local Development Setup

How to get Holus running locally from zero.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | `brew install python@3.12` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| OrbStack | latest | `brew install --cask orbstack` (replaces Docker Desktop) |
| Docker Compose | v2+ | Included with OrbStack |
| Redis CLI | latest | `brew install redis` (for kill switch and debugging) |
| Claude Code | latest | `npm install -g @anthropic-ai/claude-code` |

## Step 1: Clone and Install

```bash
git clone git@github.com:camilomartinez/holus.git
cd holus
uv sync                    # Install all dependencies from pyproject.toml
uv sync --extra dev        # Include dev dependencies (pytest, ruff, mypy)
```

## Step 2: Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Infrastructure (defaults work for local dev)
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://holus:holus@localhost:5432/holus
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
```

**Never commit `.env`.** It is in `.gitignore`.

## Step 3: Start Infrastructure Services

```bash
docker compose up -d
```

This starts:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL + pgvector | 5432 | Primary database, vector embeddings |
| Redis | 6379 | Event bus, kill switch, caching |
| Langfuse | 3000 | Observability, tracing, prompt analytics |

Verify all services are healthy:

```bash
docker compose ps                          # All should show "healthy" or "running"
redis-cli ping                             # Should return PONG
curl -s http://localhost:3000/api/public/health  # Langfuse health check
```

## Step 4: Run Database Migrations

```bash
# PostgreSQL schema setup
python -m holus db migrate
```

## Step 5: Verify Installation

```bash
# Run the test suite
uv run pytest tests/unit/ -v

# Run a quick smoke test
uv run python -m holus health

# Check configuration loading
uv run python -m holus config --show
```

## Running a Single Agent (Development Mode)

```bash
# Run the marketing agent in dev mode
uv run python -m holus agent run marketing --dev
```

## Running Tests

```bash
# Unit tests only (fast, no infrastructure needed)
uv run pytest tests/unit/ -v

# Integration tests (requires docker compose up)
uv run pytest tests/integration/ -v

# All tests with coverage
uv run pytest --cov=src/holus --cov-report=term-missing

# Type checking
uv run mypy src/holus/

# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Common Tasks

### Kill Switch (Emergency Stop)

```bash
# Stop one agent
redis-cli SET holus:kill:agent:marketing-agent '{"reason":"investigating anomaly"}'

# Stop everything
redis-cli SET holus:kill:global '{"reason":"emergency"}'

# Resume
redis-cli DEL holus:kill:agent:marketing-agent
redis-cli DEL holus:kill:global

# Check status
redis-cli KEYS "holus:kill:*"
```

### View Agent Logs

```bash
# Structured logs go to stdout in JSON format
docker compose logs -f holus-marketing

# Or check log files
tail -f logs/marketing-agent.stdout.log
```

### View Event Bus

```bash
# Subscribe to all Holus events
redis-cli PSUBSCRIBE "holus.*"

# Read event stream history
redis-cli XRANGE holus:stream:holus.marketing.content - + COUNT 10
```

---

**Last updated:** 2026-02-24
