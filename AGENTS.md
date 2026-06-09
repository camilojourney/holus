# Holus — Agent Instructions

## Project Docs Index

```
[Holus Docs Index] | root: ./
|IMPORTANT: Fetch specific files on demand, do not assume content
|architecture:  {ARCHITECTURE.md}
|specs:         {specs/README.md}
|decisions:     {docs/decisions/}
|playbooks:     {docs/playbooks/}
|roadmap:       {docs/roadmap.md}
|vision:        {docs/vision.md}
|config:        {config/base.yaml, config/guardrails.yaml, config/products.yaml}
|agent-defs:    {agents/AGENTS.yaml}
|rules:         {.claude/rules/structure.md, .claude/rules/code-style.md,
|               .claude/rules/testing.md, .claude/rules/security.md}
```

---

## What Holus Is

Holus is an **AI marketing strategist** for the product portfolio.

**Goal:** Promote Pilaster, genpeli, and invoz by creating content that resonates
with each product's audience, publishing it through the right channels,
and learning from what works to improve over time.

**How it works:**
- Observes analytics from social-media-automatization (via MCP)
- Reasons about strategy using Claude Opus
- Acts by calling silo tools: genpeli-mcp, pilaster-mcp, social-media-mcp
- Evaluates results and updates strategy

**What Holus is NOT:**
- Not a trading system (pythia + milo are completely separate, never touched)
- Not a publisher (social-media-automatization does the actual posting)
- Not a video generator (genpeli does that)
- Not an image generator (pilaster does that)

---

## Agent Registry

The single source of truth for all agents is [`agents/AGENTS.yaml`](agents/AGENTS.yaml).

Agent prompt files live in `agents/` as `.md` files with YAML frontmatter, organized by role:
- `agents/managers/` — Strategy and coordination
- `agents/specialists/` — Content production by category (written-authority, visual, video, growth, research, repurposing)
- `agents/evaluators/` — Domain-expert quality judges
- `agents/ops/` — System maintenance

Each agent file follows the KERNEL template: Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples.

---

## Agents in This System

| Agent | Model | Role |
|-------|-------|------|
| `marketing-strategist` | Opus | Primary agent — decides strategy, calls silo MCPs, learns |
| `manager` | Opus | Self-improvement orchestrator — coordinates workers, updates NEXT.md |
| `code-improver` | Sonnet | Code quality and test coverage |
| `security-sentinel` | Sonnet | Security audit, credential scanning |
| `judge-agent` | Sonnet | Evaluates worker outputs, updates lessons.json |

---

## Agent Authority Matrix

### Autonomous — No confirmation needed

- Read any file in the repository
- Run lint, type checking, and tests (`just check`)
- Call silo MCP tools to read data (analytics, product state)
- Generate content drafts (text, briefs for video/image)
- Write reports to `.self-improvement/reports/`
- Update `.self-improvement/MEMORY.md` with learned patterns
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

---

## Where Agents Write Outputs

| Output | Location | Persistence |
|--------|---------|-------------|
| Marketing reports | `.self-improvement/reports/marketing/YYYY-MM-DD.md` | Git-ignored |
| Manager reports | `.self-improvement/reports/manager/YYYY-MM-DD.md` | Git-ignored |
| Priority queue | `.self-improvement/NEXT.md` | In git |
| System memory | `.self-improvement/MEMORY.md` | In git |
| Run trajectory | `.self-improvement/memory/trajectory.jsonl` | Git-ignored |
| Lessons | `.self-improvement/memory/lessons.json` | Git-ignored |

---

## Silo Boundaries

Holus calls silos via MCP. It does NOT:
- Import silo Python packages
- Read silo databases directly
- SSH into silo servers
- Manage silo deployments

The MCP boundary is the contract. If a silo's MCP is down, Holus waits.

---

## Key Constraints

1. **Marketing only.** Holus promotes products. It does not trade, code for other repos, or manage operations outside marketing.
2. **Analytics stay in the silo.** social-media-automatization owns all analytics data. Holus reads it via MCP, never stores it permanently.
3. **Trading is isolated.** pythia and milo-to-the-moon are never referenced, called, or monitored by Holus. They are separate businesses.
4. **Human approval for publishing.** Phase 1: all publish actions require human review before execution. Phase 2+: autonomous with weekly human review.

## graphify

When the user types `/graphify`, invoke the graphify skill before doing anything else.

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
