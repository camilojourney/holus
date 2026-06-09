## Parallelism & Skills

**Always use agents to parallelize work.** Launch multiple Agent() calls for independent tasks.

**Use skills for repo work:**

| Task | Skill |
|------|-------|
| Implement, fix bugs, add API | `/code holus` |
| Write specs | `/specs holus` |
| Research options | `/research holus` |
| UX/UI audit + fix | `/ux holus` |
| Acceptance testing | `/verify holus` |
| Health check, deps, lint | `/maintenance holus` |
| Multi-step plans | `/plan holus` |
| Technical decision | `/consult-engineering holus` |
| Autonomous systems | `/consult-systems holus` |
| Business decision | `/consult-business` |
| Aesthetic quality | `/taste holus` |
| ML experiment design | `/consult-experiments holus` |

**Agent dispatch:** Claude subagents for research/analysis, Codex for implementation, Gemini for cross-model review.

# Holus

Thought-to-content studio for the product portfolio. One thought from a person or
online source becomes platform-native text, images, carousels, reviewed queue
items, scheduled/published posts, and learning signals.

## Commands

```bash
just install          # uv sync --all-extras
just run              # start the marketing agent
just check            # lint + typecheck + tests (run before committing)
just improve          # run manager self-improvement cycle
just audit            # run security sentinel
```

## What Holus Does

1. Ingests a thought from text, a person, or a URL.
2. Normalizes it into a useful source thought with source metadata.
3. Plans one content set for the requested platform activations.
4. Generates platform-native text, images, and carousels.
5. Keeps human review as the default gate.
6. Schedules or publishes explicitly through Holus Social API.
7. Reads performance snapshots from Holus Social API and improves strategy.

## Silo Tools (MCP servers Holus calls)

| Tool | Repo | What it does for Holus |
|------|------|----------------------|
| `holus-social-api` | Holus Social API | Schedule/post content + read analytics |
| `pilaster-mcp` | pilaster | Future optional AI-image adapter |
| `genpeli-mcp` | genpeli | Future optional video adapter |

## What Holus Does NOT Do

- Trading (pythia + milo are completely separate, never touched by Holus)
- Store platform analytics permanently (that data lives in Holus Social API)
- Post silently during review; publish/schedule must be explicit
- Depend on Genpeli/video for the current text, image, and carousel workflow

## Rules

- NEVER expose API keys in code or commits. All secrets via `.env`.
- ALWAYS run `just check` before committing.
- NEVER modify `config/guardrails.yaml` without explicit human approval.
- ALWAYS use Pydantic models at silo boundaries. No raw dicts.

## Type
A — Autonomous Marketing Agent (ReAct loop, 32 agents, Observatory API)

## Structure
| Path | Purpose |
|------|---------|
| `src/holus/` | Main Python package |
| `src/holus/agents/` | Agent implementations (marketing, finance, coordinator) |
| `src/holus/api/` | Observatory FastAPI API |
| `src/holus/core/` | Shared infra (config, kill_switch, models) |
| `src/holus/memory/` | Memory and learning components |
| `src/holus/visual/` | Visual content generation |
| `agents/` | Agent prompt definitions (.md + YAML frontmatter) |
| `config/` | YAML configs (base, guardrails, products) |
| `infra/` | Build scripts (build-cycle, build-sprint, init-db, launchd) |
| `infrastructure/` | Monitoring configs (prometheus, grafana, otel, alerts) |
| `knowledge/current/` | Accumulated domain knowledge |
| `observatory/` | Observatory frontend (Next.js dashboard) |
| `scripts/` | Standalone utility scripts |
| `tests/` | Test suite |
| `specs/` | Feature specifications (NNN-name.md) |
| `docs/` | Documentation (decisions/, playbooks/, vision.md, roadmap.md) |
| `pre-registrations/` | Type A: pre-registered hypotheses |
| `discussions/` | Type A: research discussions |

## Context

- Architecture: @ARCHITECTURE.md
- Rules: @.claude/rules/
- Specs: @specs/README.md
- Agent roles: @AGENTS.md
- Env template: @.env.example

@import .claude/rules/workflow.md

<!-- graphify:start -->
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- When `graphify-out/graph.json` exists and the user asks how code is structured, wired, called, or where behavior lives, first run `graphify query "<question>"`. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. Answer from query output; read at most one source file only if the query is thin or missing a named symbol.
- Before editing a source file, run `graphify query` or `graphify path` to surface dependents/callers/importers. Include connected files in the change set or explicitly call out what else must change.
- Do not re-read multiple source files after a good query unless the user asks for line-level proof.
- Skip graphify for trivial one-line edits already in context, pure shell/commit/run tasks, and external/non-repo research.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw file browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost).
<!-- graphify:end -->
