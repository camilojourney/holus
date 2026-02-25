# Playbook: Agent Session Guide

What every AI agent must do when starting a session in the Holus repo.

---

## Startup Checklist

Run these steps in order at the beginning of every session:

### 1. Read Project Context

```
1. CLAUDE.md              -- project conventions, critical rules
2. AGENTS.md              -- your role, authority matrix, doc index
3. ARCHITECTURE.md        -- system design, component relationships
```

### 2. Check Current Priorities

```
4. .self-improvement/NEXT.md           -- priority queue (what to work on next)
5. docs/roadmap.md                     -- Now/Next/Later strategic direction
6. specs/README.md                     -- feature index and status
```

### 3. Review Latest Reports

```
7. .self-improvement/reports/          -- latest reports from all workers
   - Check your worker's last report for continuity
   - Check other workers' reports for cross-cutting context
```

### 4. Check System Health

```
8. redis-cli KEYS "holus:kill:*"       -- any kill switches active?
9. docker compose ps                    -- all services running?
```

## Current Sprint Focus

Read `docs/roadmap.md` "Now" section for the current focus. All work should align with these priorities unless explicitly overridden by `.self-improvement/NEXT.md`.

## Known Blockers

Check `.self-improvement/NEXT.md` for blockers. If a blocker prevents your work:

1. Document the blocker in your report
2. Move to the next priority item
3. Do not attempt to work around blockers that involve other agents' domains

## Output Paths

| Output Type | Path | Format |
|-------------|------|--------|
| Code changes | PR against `main` | Standard PR with spec reference |
| Self-improvement reports | `.self-improvement/reports/{worker-name}/YYYY-MM-DD.md` | Markdown report |
| Trajectory data | `.self-improvement/memory/trajectory.jsonl` | Append-only JSONL |
| Lessons learned | `.self-improvement/memory/lessons.json` | Structured JSON |
| Security findings | `.self-improvement/reports/security/YYYY-MM-DD.md` | Markdown report |

## Self-Improvement Cycle

If running a self-improvement cycle:

1. **Manager agent** reads NEXT.md, selects the highest-priority improvement
2. **Code Improver agent** executes the improvement, writes code
3. **Judge agent** evaluates the result against acceptance criteria
4. **Prompt Optimizer agent** (monthly) runs DSPy optimization if 30+ labeled examples exist

After completing a cycle:

1. Write your report to the appropriate `.self-improvement/reports/` directory
2. Update `.self-improvement/NEXT.md` (mark completed, add discovered items)
3. Append to `.self-improvement/memory/trajectory.jsonl`

## What Requires Human Confirmation

From `config/guardrails.yaml` -- check the authority matrix for your specific agent. In general:

- **Autonomous:** Bug fixes, tests, docs, reports, routine operations
- **Ask first:** New dependencies, API contract changes, schema changes, config changes
- **Never:** Force-push to main, delete production data, commit secrets, disable circuit breakers, modify own guardrails

## Agent-Specific Notes

### Trading Agent Sessions
- Always check `config/trading_agent.yaml` for current guardrails
- Verify paper/live mode before any trading operations
- Check daily loss limits have not been triggered

### Content Agent Sessions
- Check content calendar in Mem0 for scheduled items
- Verify Late API connectivity before batch publishing
- Review engagement data from last 7 days

### Coding Agent Sessions
- Check open PRs across all repos for review backlog
- Run `git status` on all managed repos
- Review any @claude mentions in GitHub issues

---

**Last updated:** 2026-02-24
