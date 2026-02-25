# Repository Structure — holus

> WHERE things go in this repo. Read before creating or moving any file.
> Type E — Federated AI Operating System (multi-agent orchestrator).

## Root Level

| File/Dir | Purpose |
|----------|---------|
| `CLAUDE.md` | Claude Code quick reference (≤80 lines). |
| `AGENTS.md` | Universal AI entry point. Agent authority matrix. |
| `ARCHITECTURE.md` | Full system architecture (200-500 lines). |
| `README.md` | Human-facing project overview. |
| `justfile` | Unified task runner (`just --list` to discover). |
| `docker-compose.yml` | Local service orchestration (Redis, Postgres, n8n, Langfuse). |
| `pyproject.toml` | Python package config and dependencies (uv). |
| `.env.example` | Environment variable template. Never `.env` itself. |
| `src/` | Core Python library (`src/holus/`). |
| `config/` | Agent YAML configs: `base.yaml`, `{agent}.yaml`, `guardrails.yaml`. |
| `infra/` | Infrastructure scripts (DB init, deployment helpers). |
| `specs/` | Numbered feature specifications. |
| `docs/` | Structured documentation (four categories only). |
| `tests/` | pytest test suite (mirrors `src/holus/`). |
| `data/` | Runtime data (gitignored if large). |
| `devlog/` | Session devlog entries (YYYY-MM-DD.md). |
| `tasks/` | Temporary session task files (delete when done). |
| `.claude/` | Claude Code configuration, rules, agents. |
| `.self-improvement/` | Autonomous improvement system. |

**Never create files at root** unless they are one of the above.

## Source Code (`src/holus/`)

| Package | Purpose |
|---------|---------|
| `src/holus/core/` | Shared infrastructure: config, event bus, kill switch, logging. |
| `src/holus/agents/` | One package per domain agent (trading, content, coding, pilaster, coordinator). |
| `src/holus/integrations/` | One package per external service (alpaca, n8n, comfyui, claude_api). |
| `src/holus/memory/` | Mem0 + pgvector + trajectory logging. |
| `src/holus/observability/` | Langfuse tracing + metrics. |
| `src/holus/self_improvement/` | Judge, Prompt Optimizer, Reflexion. |

## Config (`config/`)

| File | Purpose |
|------|---------|
| `config/base.yaml` | Defaults — overridden by agent-specific files and env vars. |
| `config/guardrails.yaml` | CRITICAL safety limits — never modify without human approval. |
| `config/{agent}.yaml` | Per-agent overrides (trading.yaml, content.yaml, etc.). |

## Docs (`docs/`)

**Exactly four categories — no others.**

| Path | Purpose |
|------|---------|
| `docs/README.md` | Navigation index. |
| `docs/vision.md` | Product vision. Update at most yearly. |
| `docs/roadmap.md` | Now/Next/Later feature plan. |
| `docs/decisions/NNNN-*.md` | ADRs — immutable once accepted. |
| `docs/playbooks/*.md` | Step-by-step operational guides. |

**NEVER create** ad-hoc files in `docs/`. Architecture → `ARCHITECTURE.md` (root). Specs → `specs/`.

## Specs (`specs/`)

Numbered feature specs: `specs/NNN-name.md`. Flat structure only. No subdirectories.

## `.claude/` — Claude Code Configuration

| Path | Purpose |
|------|---------|
| `.claude/settings.json` | Permissions and hooks. |
| `.claude/rules/*.md` | Behavioral rules (structure, code-style, testing, security). |
| `.claude/agents/*.md` | Agent definitions for `just improve`, `just audit`, etc. |
| `.claude/agent-memory/<agent>/` | Per-agent runtime memory (gitignored). |

## `.self-improvement/`

| Path | Purpose |
|------|---------|
| `.self-improvement/workers.yaml` | Worker registry. |
| `.self-improvement/NEXT.md` | Priority queue (Manager writes, all workers read). |
| `.self-improvement/MEMORY.md` | Domain knowledge and lessons learned. |
| `.self-improvement/memory/trajectory.jsonl` | Append-only run log (gitignored). |
| `.self-improvement/memory/lessons.json` | Distilled patterns (gitignored). |
| `.self-improvement/reports/<worker>/YYYY-MM-DD.md` | Per-worker output (gitignored). |

## What Goes Where

| Content | Location |
|---------|---------|
| New feature spec | `specs/NNN-name.md` |
| Architecture decision | `docs/decisions/NNNN-name.md` |
| Operational guide | `docs/playbooks/name.md` |
| New domain agent | `src/holus/agents/{name}/` |
| External API client | `src/holus/integrations/{service}/` |
| Shared utility | `src/holus/core/` |
| Unit test | `tests/unit/{package}/test_{module}.py` |
| Agent config | `config/{agent}.yaml` |
| Dev session notes | `devlog/YYYY-MM-DD.md` |
| Agent priorities | `.self-improvement/NEXT.md` |
| Worker reports | `.self-improvement/reports/<worker>/YYYY-MM-DD.md` |
| Infra scripts | `infra/` |
