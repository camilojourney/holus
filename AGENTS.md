# AGENTS.md

# Holus

Thought-to-content studio for the product portfolio. One thought from a person or
online source becomes platform-native text, images, carousels, reviewed queue
items, scheduled/published posts, and learning signals.

## Project Docs Index

```
[Holus Docs Index] | root: ./
|IMPORTANT: Fetch specific files on demand, do not assume content
|architecture:  {ARCHITECTURE.md}
|specs:         {specs/README.md}
|decisions:     {docs/decisions/}
|playbooks:     {agentic/playbooks/}
|roadmap:       {docs/roadmap.md}
|vision:        {docs/vision.md}
|config:        {config/base.yaml, config/guardrails.yaml, config/products.yaml}
|agent-defs:    {agentic/agents/AGENTS.yaml}
|rules:         {.claude/rules/structure.md, .claude/rules/code-style.md,
|               .claude/rules/testing.md, .claude/rules/security.md}
```

## What Holus Is

Holus is an **AI marketing strategist** for the product portfolio.

**Goal:** Promote Pilaster, genpeli, and invoz by creating content that resonates
with each product's audience, publishing it through the right channels,
and learning from what works to improve over time.

**How it works:**
- Observes analytics from Holus Social API (via MCP/API boundary)
- Reasons about strategy using Claude Opus
- Acts by calling silo tools: genpeli-mcp, pilaster-mcp, social-media-mcp
- Evaluates results and updates strategy

**What Holus is NOT:**
- Not a trading system (pythia + milo are completely separate, never touched)
- Not a silent publisher (Holus Social API owns actual posting)
- Not a video generator (genpeli does that)
- Not an image generator (pilaster does that)

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

## Type

A — Autonomous Marketing Agent (ReAct loop, 44 agents, Observatory API)

## Structure

| Path | Purpose |
|------|---------|
| `src/holus/` | Main Python package |
| `src/holus/agents/` | Agent implementations (marketing, finance, coordinator) |
| `src/holus/api/` | Observatory FastAPI API |
| `src/holus/core/` | Shared infra (config, kill_switch, models) |
| `src/holus/memory/` | Memory and learning components |
| `src/holus/visual/` | Visual content generation |
| `agentic/` | Agentic control plane: agents, workflows, playbooks, skills, memory policy |
| `agentic/agents/` | Agent prompt definitions (.md + YAML frontmatter) |
| `agentic/workflows/` | Platform workflow specs |
| `agentic/playbooks/` | Operational playbooks |
| `agentic/memory/` | Durable semantic memory, knowledge, and thought harness ledgers |
| `config/` | YAML configs (base, guardrails, products) |
| `infra/` | Build scripts (build-cycle, build-sprint, init-db, launchd) |
| `infrastructure/` | Monitoring configs (prometheus, grafana, otel, alerts) |
| `observatory/` | Observatory frontend (Next.js dashboard) |
| `scripts/` | Standalone utility scripts |
| `tests/` | Test suite |
| `specs/` | Feature specifications (NNN-name.md) |
| `docs/` | Documentation outside the agentic control plane (decisions/, vision.md, roadmap.md) |
| `pre-registrations/` | Type A: pre-registered hypotheses |
| `discussions/` | Type A: research discussions |

## Commands

```bash
just install          # uv sync --all-extras (plain `uv sync` also installs dev deps)
just run              # start the marketing agent
just check            # lint + typecheck + tests (run before committing)
just improve          # run manager self-improvement cycle
just audit            # run security sentinel
```

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

## Agent Registry

The single source of truth for all agents is [`agentic/agents/AGENTS.yaml`](agentic/agents/AGENTS.yaml).

Agent prompt files live in `agentic/agents/` as `.md` files with YAML frontmatter, organized by role:
- `agentic/agents/managers/` — Strategy and coordination
- `agentic/agents/specialists/` — Content production by category (written-authority, visual, video, growth, research, repurposing)
- `agentic/agents/evaluators/` — Domain-expert quality judges
- `agentic/agents/ops/` — System maintenance

Each agent file follows the KERNEL template: Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples.

## Agents in This System

| Agent | Model | Role |
|-------|-------|------|
| `marketing-strategist` | Opus | Primary agent — decides strategy, calls silo MCPs, learns |
| `manager` | Opus | Self-improvement orchestrator — coordinates workers, updates NEXT.md |
| `code-improver` | Sonnet | Code quality and test coverage |
| `security-sentinel` | Sonnet | Security audit, credential scanning |
| `judge-agent` | Sonnet | Evaluates worker outputs, updates lessons.json |

## Agent Authority Matrix

### Autonomous — No confirmation needed

- Read any file in the repository
- Run lint, type checking, and tests (`just check`)
- Call silo MCP tools to read data (analytics, product state)
- Generate content drafts (text, briefs for video/image)
- Write reports to `.self-improvement/reports/`
- Update `agentic/memory/MEMORY.md` with learned patterns
- Fix bugs that don't touch auth, billing, or silo API contracts

### Ask First — Propose, wait for approval

- Call silo MCP tools to POST or publish (schedule_post, create_video)
- Change which products are being promoted in `config/products.yaml`
- Change which platforms or accounts are targeted
- Add or remove dependencies in `pyproject.toml`
- Change Pydantic models used at silo boundaries
- Modify `config/*.yaml` configuration files
- Spend more than $5/day on generation API calls

### Never — Hard stop, escalate immediately

- Expose API keys, secrets, or credentials in code or commits
- Force-push to main
- Access pythia, milo-to-the-moon, or any trading system
- Modify `config/guardrails.yaml` without explicit human approval
- Delete content performance data or trajectory logs
- Post content about trading, financial advice, or investment decisions
- Access social media accounts not listed in `config/products.yaml`

## Where Agents Write Outputs

| Output | Location | Persistence |
|--------|---------|-------------|
| Marketing reports | `.self-improvement/reports/marketing/YYYY-MM-DD.md` | Git-ignored |
| Manager reports | `.self-improvement/reports/manager/YYYY-MM-DD.md` | Git-ignored |
| Priority queue | `agentic/memory/NEXT.md` | In git |
| System memory | `agentic/memory/MEMORY.md` | In git |
| Run trajectory | `.self-improvement/memory/trajectory.jsonl` | Git-ignored |
| Lessons | `.self-improvement/memory/lessons.json` | Git-ignored |

## Silo Boundaries

Holus calls silos via MCP. It does NOT:
- Import silo Python packages
- Read silo databases directly
- SSH into silo servers
- Manage silo deployments

The MCP boundary is the contract. If a silo's MCP is down, Holus waits.

## Rules

- NEVER expose API keys in code or commits. All secrets via `.env`.
- ALWAYS run `just check` before committing.
- NEVER modify `config/guardrails.yaml` without explicit human approval.
- ALWAYS use Pydantic models at silo boundaries. No raw dicts.

## Key Constraints

1. **Marketing only.** Holus promotes products. It does not trade, code for other repos, or manage operations outside marketing.
2. **Analytics stay in the silo.** Holus Social API owns all analytics data. Holus reads it via MCP/API boundary, never stores it permanently.
3. **Trading is isolated.** pythia and milo-to-the-moon are never referenced, called, or monitored by Holus. They are separate businesses.
4. **Human approval for publishing.** Phase 1: all publish actions require human review before execution. Phase 2+: autonomous with weekly human review.
5. **Public generation stays Holus-owned.** The browser never calls Genpeli, and public/demo Observatory never opens localhost SSE. See the public generation boundary in `ARCHITECTURE.md`.

## Context

- Architecture: @ARCHITECTURE.md
- Rules: @.claude/rules/
- Specs: @specs/README.md
- Env template: @.env.example

@import .claude/rules/workflow.md

<!-- graphify:start -->
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- When `graphify-out/graph.json` exists and the user asks how code is structured, wired, called, or where behavior lives, first run `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py query "<question>"`. Use `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py path "<A>" "<B>"` for relationships and `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py explain "<concept>"` for focused concepts. Answer from query output; read at most one source file only if the query is thin or missing a named symbol.
- Before editing a source file, run the traceable `fleet_graphify.py query` or `fleet_graphify.py path` wrapper to surface dependents/callers/importers. Include connected files in the change set or explicitly call out what else must change.
- Do not re-read multiple source files after a good query unless the user asks for line-level proof.
- Skip graphify for trivial one-line edits already in context, pure shell/commit/run tasks, and external/non-repo research.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw file browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code files in this session, run `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py update .` to keep the graph current (AST-only, no API cost).
- After modifying docs, notes, images, `AGENTS.md`, `CLAUDE.md`, or `ai-instructions/`, use `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py . --update` or the installed AGY semantic hook wrapper. Fleet default semantic runner is `agy --model "Gemini 3.5 Flash (Medium)"`.
- In worktrees, use the worktree-local `graphify-out/`; do not share or symlink one graph across active branches.
<!-- graphify:end -->

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
