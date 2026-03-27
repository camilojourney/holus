# Phase 3: Quality Review + Ship — 20 Parallel Agents

**Goal:** Every dimension of quality reviewed by a specialist. Merge conflicts resolved. Specs updated.
**Done when:** All tests pass, all pages render, taste >= 8/10, architecture approved, specs README current.
**Gate:** hard — user approves before committing all changes.

## Quality Review Agents (15 parallel)

Each reviews ONE dimension across the ENTIRE system.

| # | Agent | Dimension | Skill | What It Checks |
|---|-------|----------|-------|---------------|
| Q1 | `taste-brand` | Brand consistency | `/taste holus` | Does Observatory match brand.yaml? Colors, fonts, voice? |
| Q2 | `taste-content` | Content quality | `/taste holus` | Sample generated content in data/ — authority bar met? |
| Q3 | `taste-prompts` | Prompt quality | `/taste holus` | All 35+ agent prompts — specific, clear, brand-aligned? |
| Q4 | `taste-ux` | Observatory UX | `/taste holus` | Does dashboard feel premium? Layout, typography, polish? |
| Q5 | `eng-architecture` | Architecture | `/consult-engineering holus` | Design smells, circular deps, over-engineering? |
| Q6 | `eng-mcp` | MCP design | `/consult-engineering holus` | Integration pattern correct? Boundaries clean? |
| Q7 | `eng-testing` | Test strategy | `/consult-engineering holus` | Right balance unit/integration/e2e? Gaps identified? |
| Q8 | `sys-learning` | Learning loop | `/consult-systems holus` | Self-improvement stable? Can it diverge or oscillate? |
| Q9 | `sys-autonomous` | Autonomous safety | `/consult-systems holus` | Sprint loop safe? Kill switch effective? Failure modes? |
| Q10 | `exp-rubrics` | Evaluator design | `/consult-experiments holus` | 7 rubrics well-designed? Blind spots? Inter-rater? |
| Q11 | `biz-strategy` | Marketing strategy | `/consult-business` | Right products, right order, right platforms for revenue? |
| Q12 | `verify-acceptance` | Acceptance criteria | `/verify holus` | docs/acceptance-criteria.md passes against current code |
| Q13 | `verify-frontend` | Frontend rendering | `/verify holus` | All 13 pages render, no console errors, build passes |
| Q14 | `maint-deps` | Dependencies | `/maintenance holus` | Outdated deps, security vulns, lock file clean |
| Q15 | `maint-lint` | Code quality | `/maintenance holus` | ruff + mypy clean, no warnings |

## Integration Fix Agents (5 sequential, after quality)

| # | Agent | Task | Skill |
|---|-------|------|-------|
| F1 | `fix-conflicts` | Resolve any merge conflicts from Wave 2 parallel edits | `/code holus` |
| F2 | `fix-quality-findings` | Address critical findings from quality agents | `/code holus` |
| F3 | `wire-new-modules` | Ensure diagnostician, bandit, visual registry are called from agent loop | `/code holus` |
| F4 | `update-specs` | Update every spec status in specs/README.md | `/code holus` |
| F5 | `final-check` | Run `just check` — must pass clean | `/verify holus` |

## Key Questions for Quality Agents

### Architecture Review (Q5)
- Is the 130-file structure justified or bloated?
- Are there modules that should be merged?
- Is the agent → core → integration layering clean?
- Any circular imports?

### Learning Loop Review (Q8)
- Can the judge scores drift without detection?
- Can prompt evolution make prompts worse over time?
- Is there a rollback mechanism for bad prompt mutations?
- Does the knowledge archive rotation lose important data?

### Marketing Strategy Review (Q11)
- Is promoting Pilaster, Genpeli, Invoz in the right order?
- Is LinkedIn the right primary platform?
- Is the content mix (tutorials, authority posts, demos) optimal?
- What's the expected time to first revenue from content?

## Output

- `results/phase-03-quality-report.md` — all 15 quality verdicts compiled
- `results/phase-03-integration-log.md` — what was fixed, wired, updated
- `results/phase-03-final-check.md` — `just check` output (must be clean)
- `results/summary.md` — complete sprint summary

## Gate

**HARD GATE.** Present to user:
1. Quality scores from all 15 dimensions
2. Files changed count
3. Tests added count
4. Coverage delta
5. Any critical findings unresolved

User approves → commit all changes as one atomic commit.
User rejects → list what to fix, re-run targeted agents.
