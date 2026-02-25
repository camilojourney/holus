# Holus — unified task runner
# Run `just` or `just --list` to see all commands.

default:
    @just --list

# -- Setup -------------------------------------------------------------------

install:
    uv sync --all-extras

# -- Run ---------------------------------------------------------------------

run:
    python -m holus

run-agent agent:
    python -m holus agent start {{agent}}

run-all:
    python -m holus agent start --all

# -- Test --------------------------------------------------------------------

test:
    pytest tests/ -x -v

test-unit:
    pytest tests/unit/ -x -v

test-integration:
    pytest tests/integration/ -x -v

test-cov:
    pytest tests/ --cov=src/holus --cov-report=term-missing --cov-report=html

# -- Code Quality ------------------------------------------------------------

lint:
    ruff check src/ tests/
    mypy src/

format:
    ruff format src/ tests/
    ruff check src/ tests/ --fix

format-check:
    ruff format src/ tests/ --check

check: lint format-check test

# -- Docker / Infrastructure -------------------------------------------------

up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

reset:
    docker compose down -v

# -- Utilities ---------------------------------------------------------------

clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

# -- Self-Improvement --------------------------------------------------------

improve:
    claude --agent .claude/agents/manager.md

audit:
    claude --agent .claude/agents/security-sentinel.md
