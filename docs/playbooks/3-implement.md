# Phase 3: Implementation

Implement approved specs with tests and minimal scope drift.

## Rules

- follow existing architecture patterns
- implement in dependency order
- add tests with each behavior change
- avoid unrelated refactors
- escalate risk per `.ai/decision-boundaries.md`

## Verification

Run commands from `AGENTS.md`:
- `flake8 core/ agents/ tools/`
- `python -m pytest tests/`
- `No build step (runtime Python app)`

## Output

- summary of implemented specs
- files changed
- tests added/updated
- verification results
- known risks/follow-ups
