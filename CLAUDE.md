# Holus

AI marketing strategist for the product portfolio. Decides what content to create,
calls silo tools to produce it, tracks what works, and improves strategy over time.

## Commands

```bash
just install          # uv sync --all-extras
just run              # start the marketing agent
just check            # lint + typecheck + tests (run before committing)
just improve          # run manager self-improvement cycle
just audit            # run security sentinel
```

## What Holus Does

1. Reads analytics from social-media-automatization (what performed well)
2. Reads product state (what's new in Pilaster, genpeli, invoz)
3. Decides what content to create and for which product
4. Calls silo tools (genpeli MCP, pilaster MCP, social-media MCP) to execute
5. Tracks results. Adjusts strategy.

## Silo Tools (MCP servers Holus calls)

| Tool | Repo | What it does for Holus |
|------|------|----------------------|
| `genpeli-mcp` | genpeli | Create and edit videos |
| `social-media-mcp` | social-media-automatization | Post content + read analytics |
| `pilaster-mcp` | pilaster | Generate images, run workflows |

## What Holus Does NOT Do

- Trading (pythia + milo are completely separate, never touched by Holus)
- Store social media analytics (that data lives in social-media-automatization)
- Publish content directly (social-media-automatization does that)
- Generate videos itself (genpeli does that)

## Rules

- NEVER expose API keys in code or commits. All secrets via `.env`.
- ALWAYS run `just check` before committing.
- NEVER modify `config/guardrails.yaml` without explicit human approval.
- ALWAYS use Pydantic models at silo boundaries. No raw dicts.

## Context

- Architecture: @ARCHITECTURE.md
- Rules: @.claude/rules/
- Specs: @specs/README.md
- Agent roles: @AGENTS.md
- Env template: @.env.example

@import .claude/rules/workflow.md
