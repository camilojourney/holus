# Workflow: Explore → Plan → Execute → Review

## Core Principle

**When the user says do something, do it.** No asking "should I proceed?", no "want me to launch?", no confirmation prompts. Explore, plan, execute — just go. Report results, not intentions.

## Roles

| Where | Who | Does what | Approvals needed |
|-------|-----|-----------|-----------------|
| VS Code | Opus 4.6 | Explores, plans, launches agents, reviews results | None |
| Background CLI | `claude -p` agent | Implements, tests, commits | None (`--dangerously-skip-permissions`) |

**Opus in VS Code never writes code directly.** It explores, plans, launches autonomous CLI agents in the background, and reviews results. All code changes happen through background agents. The user never leaves the conversation.

## Execution Method

Opus launches CLI agents in the background using the Bash tool:

```bash
env -u CLAUDECODE claude --dangerously-skip-permissions --model [model] --max-turns [N] --output-format text -p '...' > /tmp/cycle-output.txt 2>&1
```

Key details:
- `env -u CLAUDECODE` — required to allow nested Claude sessions
- `--output-format text` — captures the agent's final response
- `> /tmp/cycle-output.txt 2>&1` — redirects output to a file Opus can read back
- `run_in_background: true` on the Bash tool — so the conversation continues while the agent works

**CRITICAL: Never block-wait on background tasks.** After launching a cycle, do NOT call `TaskOutput` with `block: true`. Instead, stay available to the user. When the system sends a background task completion notification, read the output file then. Blocking makes Opus unresponsive — the whole point is to keep talking while agents work.

**The user never copies, pastes, or switches windows.** Opus manages the full cycle.

## The Four Phases

### Phase 1 — Explore (VS Code, parallel)
Spawn multiple explore agents to understand the codebase fast. Read-only, no approvals.
- Use `subagent_type=Explore` for codebase research
- Launch as many as needed in parallel (8+ is fine)
- Goal: understand the current state before planning

### Phase 2 — Plan (VS Code, Opus thinks)
Write specs and break work into execution cycles.
- Write spec files to `specs/NNN-feature.md` for complex features
- For simple tasks, skip specs — put instructions directly in the `-p` prompt
- Break large features into numbered cycles
- Tell the user the plan and how many cycles, then immediately start launching

### Phase 3 — Execute (background CLI agents, sequential cycles)
Opus launches each cycle as a background Bash command. When one finishes, Opus reads the output, reports to the user, and launches the next automatically.

```
Opus: "Launching Cycle 1 (Sonnet — implement backend)..."
  → agent runs in background
  → conversation continues
Opus: "Cycle 1 done. Tests pass. 2 files changed. Launching Cycle 2..."
  → next agent runs automatically, no asking
Opus: "Cycle 2 done. Opus review found 1 issue. Launching Cycle 3 to fix..."
Opus: "All clean. Feature complete. 3 commits."
```

**Use the right model for the job:**

| Cycle type | Model | Flag | Why |
|------------|-------|------|-----|
| Implementation | Sonnet 4.6 | `--model claude-sonnet-4-6` | Fast, good enough for straightforward coding |
| Complex implementation | Opus 4.6 | `--model claude-opus-4-6` | Architectural decisions, tricky logic |
| Test + fix | Sonnet 4.6 | `--model claude-sonnet-4-6` | Mechanical — run tests, fix failures |
| Quality review + fix | Opus 4.6 | `--model claude-opus-4-6` | Catches subtle bugs, design issues |
| Simple cleanup | Haiku 4.5 | `--model claude-haiku-4-5-20251001` | Formatting, renames, trivial changes |

### Phase 4 — Review (VS Code, Opus)
After all cycles complete, Opus reviews the full diff.
- If issues found: launch a targeted fix cycle automatically
- If clean: done, report to user

## Quality Through Cycles

One pass is rarely enough for quality. Use multiple cycles:

```
Cycle 1 (Sonnet) — Implement the feature
Cycle 2 (Sonnet) — Run tests, fix failures
Cycle 3 (Opus)   — Review for quality, fix issues
Cycle 4 (Sonnet) — Final test + lint pass (if needed)
```

For critical or complex features, add more cycles. For simple changes, one cycle may be enough. **Opus recommends the number of cycles based on complexity.**

### Verification in Every Cycle
Every cycle prompt must include an iterative verification loop — not just "run tests" but "run, fix, repeat until green":

```
Run pnpm test. If any tests fail, fix them and run again. Repeat until all tests pass.
Run pnpm eslint . — fix any lint issues found.
Run cd frontend && pnpm tsc --noEmit — fix any type errors.
Only commit when everything passes.
```

### Cycle Handoff
When cycles build on each other, include context for the next agent. The cycle prompt should reference what the previous cycle did:

```
Previous cycle implemented the backend handlers for profile optimization.
This cycle: implement the frontend components that call those endpoints.
```

## CLI Agent Command Format

### Base Command
```bash
env -u CLAUDECODE claude --dangerously-skip-permissions --model [model] --max-turns [N] --output-format text -p '...' > /tmp/cycle-N-output.txt 2>&1
```

### Flags
| Flag | Purpose |
|------|---------|
| `--dangerously-skip-permissions` | Full autonomy, no prompts |
| `--model [id]` | Choose the right model for the cycle |
| `--max-turns N` | Cap turns to prevent runaway (50 for large, 30 for medium) |
| `--output-format text` | Get readable output for review |

### Syntax Rules
- **Single quotes only** for the `-p` wrapper (zsh expands `!` and `$` in double quotes)
- All flags must come **BEFORE** `-p`
- `env -u CLAUDECODE` must prefix the command
- Reference the spec file so the agent reads it first
- Every command includes iterative test/lint/type verification + commit instruction
- Output redirected to a unique file per cycle (`/tmp/cycle-1-output.txt`, etc.)

## Fallback: Copy-Paste Mode

If background execution fails for any reason, fall back to generating commands for the user to paste:

```bash
claude --dangerously-skip-permissions --model claude-sonnet-4-6 -p 'Read specs/NNN-feature.md. Implement it fully. Run pnpm test and pnpm eslint . when done. Commit.'
```

The user pastes into a terminal, waits for completion, comes back.

## Behavior Rules for Opus (VS Code)

1. **When the user says do it, just do it** — no asking for confirmation, no "should I proceed?"
2. **Recommend the number of cycles** based on feature complexity
3. **Pick the right model** for each cycle — don't use Opus for mechanical work
4. **Tell the user the plan briefly, then start launching** — don't wait for approval
5. **Each cycle must be independently safe** — tests pass after every cycle
6. **Include the commit instruction** — the agent commits its own work
7. **Report after each cycle** — what happened, what's next
8. **Auto-launch next cycles** — don't ask between cycles, just go
9. **Stay responsive** — never block-wait on background tasks

## Worktree Isolation (optional, Opus decides)

For risky changes (schema migrations, large refactors, architectural rewrites), Opus may run a cycle in an isolated git worktree. If the agent fails or produces bad output, the worktree is discarded — main is untouched.

When to use:
- Schema or migration changes
- Refactors touching 10+ files
- Experimental approaches where rollback is likely
- Any change where "just revert the commit" isn't clean enough

When NOT to use (default):
- Normal feature implementation
- Bug fixes
- Test/lint cycles
- Anything where a simple `git revert` suffices

To enable: add `--worktree` to the `claude` command or use `isolation: worktree` on subagents.

## Phase Sequencing (within cycles)
- **Backend first** (schema, handlers, routes) — tests verify API behavior
- **Extension second** (content scripts, popup) — manual testing
- **Frontend last** (React components, hooks) — depends on backend

## When to Skip Specs
- Bug fixes — describe inline in the prompt
- Renames / cleanup — describe inline
- Single-file changes — describe inline
- Anything that takes < 1 cycle

## When Specs Are Required
- New features touching 3+ files
- Schema changes
- Architectural decisions
- Anything the user wants to review before execution

## Package Manager
- Always **pnpm** (not npm). Project uses `pnpm-lock.yaml`.
- Commands: `pnpm test`, `pnpm dev`, `pnpm eslint .`

## Commit Style
- Descriptive messages with `feat:`, `fix:`, `chore:` prefixes
- Exclude runtime data files (e.g., `data/.pipeline-state.json`)
- Co-Author-By trailer for Claude
