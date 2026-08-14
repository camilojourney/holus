# Holus

Holus -- Thought Studio and Social API workflow for a solo founder.

**Status:** Active implementation | **Version:** 0.1.0

## Quick Start

```bash
git clone https://github.com/camilomartinez/holus.git && cd holus
uv sync --all-extras
just run
```

## What This Does

Holus is a thought-to-content studio. One thought from a person or online source
becomes a content set: platform-native text, images, carousels, review decisions,
schedule requests, publish results, and learning signals.

The core loop is:

```text
thought source -> normalize -> plan content set -> generate platform variants
-> create visual assets -> review -> schedule/post via Holus Social API -> learn
```

Holus Social API is the publishing and analytics boundary. Holus prepares and
reviews content; the Social API owns accounts, posting, scheduling, and platform
analytics. Genpeli/video remains a future adapter, not a blocker for the current
text/image/carousel build.

The public Holus experience is a safe demonstration: it presents a local,
bounded generation lifecycle without creating a job or contacting Genpeli.
Holus owns the presentation and the future authenticated backend boundary; see
[ARCHITECTURE.md](ARCHITECTURE.md) for the public generation contract.

## Research Radar

Research Radar ingests recent arXiv, Hacker News, and configured RSS items,
deduplicates and scores them, then writes reviewable digests and thought
candidates under `data/research/`. Configure sources and thresholds in
`config/research.yaml`, and edit curator context in
`config/research-interests.md`.

```bash
uv run python scripts/research_radar_cycle.py
```

The `/api/v1/research` API can run the radar, read digests, list candidates,
and explicitly approve or reject candidates. Approval routes a candidate
through the Thought Studio pipeline; it does not publish content.

Validate representative text and URL intake cases without fetching URLs or
writing queue records with:

```bash
uv run python scripts/simulate_content_intake_cases.py
```


## Workflow: Explore → Plan → Execute → Review

Opus in VS Code plans and launches autonomous CLI agents in the background — the user never leaves the conversation. Agents run via `env -u CLAUDECODE claude --dangerously-skip-permissions --model [model] -p '...'` with output redirected to files. Multiple cycles ensure quality: Sonnet implements, Opus reviews. See `.claude/rules/workflow.md` for full details.

## Key Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) -- System design, component map, data flow
- [specs/README.md](specs/README.md) -- Feature specs index
- [docs/roadmap.md](docs/roadmap.md) -- Now / Next / Later roadmap
- [AGENTS.md](AGENTS.md) -- Agent roles, authority matrix, memory model
