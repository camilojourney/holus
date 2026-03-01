# Holus

Holus -- Federated AI Operating System for a Solo Founder.

**Status:** Pre-implementation | **Version:** 0.1.0

## Quick Start

```bash
git clone https://github.com/camilomartinez/holus.git && cd holus
uv sync --all-extras
make run
```

## What This Does

Holus is a federated multi-agent system that coordinates four domain-specific AI agents -- Trading, Content, Coding, and Pilaster (ComfyUI) -- across a solo founder's project portfolio. Each agent runs as an independent process with its own memory scope (Mem0), LangGraph execution graph, and event publishing channel, connected through a Redis pub/sub event bus.

The core design principle is **process-isolated federation**: agents operate independently so a crash in one never affects another, while a shared event bus and a lightweight Coordinator agent (running Claude Opus 4 daily) synthesize cross-project intelligence. This architecture starts simple and converges toward orchestration only after independent agents have proven stable.

The system includes a self-improvement loop where agents publish structured events, the Coordinator identifies cross-project patterns, and DSPy/Reflexion optimize prompts over time. A global kill switch, per-agent circuit breakers, and a codified authority matrix ensure governance at every level.


## Workflow: Explore → Plan → Execute → Review

Opus in VS Code plans and launches autonomous CLI agents in the background — the user never leaves the conversation. Agents run via `env -u CLAUDECODE claude --dangerously-skip-permissions --model [model] -p '...'` with output redirected to files. Multiple cycles ensure quality: Sonnet implements, Opus reviews. See `.claude/rules/workflow.md` for full details.

## Key Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) -- System design, component map, data flow
- [specs/README.md](specs/README.md) -- Feature specs index
- [docs/roadmap.md](docs/roadmap.md) -- Now / Next / Later roadmap
- [AGENTS.md](AGENTS.md) -- Agent roles, authority matrix, memory model
