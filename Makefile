# ==============================================================================
# Holus Makefile
# ==============================================================================

.PHONY: install run test lint format check docker-up docker-down clean help

# -- Setup --------------------------------------------------------------------

install: ## Install all dependencies (dev included)
	uv sync --all-extras

# -- Run ----------------------------------------------------------------------

run: ## Start Holus coordinator
	python -m holus

run-agent: ## Start a single agent (usage: make run-agent AGENT=trading)
	python -m holus agent start $(AGENT)

run-all: ## Start all agents
	python -m holus agent start --all

# -- Test ---------------------------------------------------------------------

test: ## Run all tests
	pytest tests/ -x -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -x -v

test-integration: ## Run integration tests (requires Docker services)
	pytest tests/integration/ -x -v

test-cov: ## Run tests with coverage report
	pytest tests/ --cov=src/holus --cov-report=term-missing --cov-report=html

# -- Code Quality -------------------------------------------------------------

lint: ## Run linter and type checker
	ruff check src/ tests/
	mypy src/

format: ## Auto-format code
	ruff format src/ tests/
	ruff check src/ tests/ --fix

format-check: ## Check formatting without modifying
	ruff format src/ tests/ --check

check: lint format-check test ## Run all checks (lint + format check + tests)

# -- Docker / Infrastructure --------------------------------------------------

docker-up: ## Start all infrastructure services
	docker compose up -d

docker-down: ## Stop all infrastructure services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

docker-reset: ## Stop services and remove volumes (DESTRUCTIVE)
	docker compose down -v

# -- Utilities ----------------------------------------------------------------

clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

# -- Help ---------------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
