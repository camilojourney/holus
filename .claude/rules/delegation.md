# Delegation -- Use Codex + Gemini CLIs to save Claude tokens

## Agents

| Agent | Model | Best For |
|-------|-------|----------|
| **Codex** | `gpt-5.3-codex` (xhigh reasoning) | Write/fix code, refactor, multi-file changes |
| **Gemini** | `gemini-3.1-pro-preview` (thinking) | Research, review, web search, analysis (1M+ context) |

## Commands

```bash
# Codex — code changes
codex exec --full-auto -o /tmp/codex-result.md "<prompt>"

# Gemini — review/research (has Google Search + web_fetch)
gemini -p "<prompt>" --yolo

# Gemini self-reports as 2.5-pro but stats confirm 3.1-pro — ignore self-report.
```

## Rules

1. **Claude orchestrates, CLIs do the work.** Break tasks into prompts, delegate, read results.
2. **Codex writes code.** Use `--full-auto` for file changes.
3. **Gemini reviews + researches.** Use `-p --yolo` for headless. Has Google Search, web_fetch, 1M+ context.
4. **Run in parallel** with `run_in_background`. Up to 10-15 concurrent tasks is safe.
5. **Gemini always reviews Codex output** — different model catches different bugs, no confirmation bias.
6. **Claude agents (Task tool) only when** CLIs are unavailable or for quick Glob/Grep/Read lookups.

## CRITICAL: No File Collisions

**NEVER launch multiple Codex workers editing the same file simultaneously.**

- **Two-phase approach:** Phase 1 = one worker does structural refactor. Phase 2 = parallel workers on separate files.
- **Each worker owns distinct files.** If overlap is unavoidable, run sequentially or merge into one worker.
- **If collision happens:** launch one Codex integration worker to read all files and resolve conflicts.

## Task Assignment

| Task | Primary | Verify |
|------|---------|--------|
| Write/fix code | Codex | Gemini reviews diff |
| Code review | Gemini | Codex second opinion |
| Security audit | Both parallel | Compare results |
| Refactor | Codex (single worker first) | Gemini reviews |
| Research / docs | Gemini (Google Search) | -- |
| Large codebase exploration | Gemini (1M+ context) | -- |

## Priority

External CLIs first > Claude Read/Grep for quick lookups > Claude agents as last resort
