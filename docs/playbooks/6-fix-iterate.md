# Phase 6: Fix and Iterate

Apply minimal, targeted fixes from audits.

## Rules

- fix only listed issues
- one focused change at a time
- preserve existing behavior
- add regression tests for each fix

## Verification

Run commands from `AGENTS.md`:
- `python -m pytest tests/`
- `flake8 core/ agents/ tools/`
- `No build step (runtime Python app)`

## Output

- issue-to-fix mapping
- changed files
- deferred items with rationale
- verification status
