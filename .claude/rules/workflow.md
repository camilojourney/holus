# Workflow

Inherits all rules from the workspace workflow (`../../.claude/rules/workflow.md`).

## Holus-Specific Overrides

- **Package manager:** `uv` (not pnpm). Commands: `uv run pytest -q`, `uv run ruff check .`
- **Verification:** `just check` (runs lint + typecheck + tests)
- **Never modify** `config/guardrails.yaml` without explicit human approval
