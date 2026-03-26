# Holus — 1000-Hour Quality Engine Plan

**Source:** ADR-009 (docs/decisions/009-2026-03-26-1000-hour-quality-engine-plan.md)
**Created:** 2026-03-26
**Total budget:** ~$140 API spend across 1000 hours

## Critical Finding

> The system has never self-improved. 35 agents, 7 evaluators, a diagnostician,
> bandits, prompt evolution, DSPy — none have ever modified a prompt or changed
> content strategy in response to data. This is a sophisticated observation
> machine with no actuators.

**Priority #1: Publish content and close the feedback loop.**

## Phases

| Phase | Hours | Goal | Budget |
|-------|-------|------|--------|
| [Phase 1](phase-1-close-the-loop.md) | 0-200 | Publish 50 pieces, close feedback loop | ~$25 |
| [Phase 2](phase-2-scale-the-data.md) | 200-400 | 5K+ posts in corpus, 100 published | ~$35 |
| [Phase 3](phase-3-self-improvement-engine.md) | 400-700 | System improves itself | ~$45 |
| [Phase 4](phase-4-scale-and-polish.md) | 700-1000 | Multi-format, multi-language, autonomy | ~$55 |

## How to Use

Each phase file has tasks with:
- Detailed description of what to build
- Files to read/modify
- Acceptance criteria
- Dependencies on other tasks
- Estimated hours

Work through tasks in order within each phase. Don't start Phase N+1 until
Phase N's deliverable is met.

## Quick Wins (Start Tomorrow)

```bash
# These take <10 hours combined and have outsized impact:
# 1. Upgrade bandit to Thompson Sampling (4h)
# 2. Lower evolution gate 500 → 100 (1h)
# 3. Fix judge default to Haiku (1h)
# 4. Build personal-context.json (2h)
# 5. Generate 5 pieces with real judges (2h)
```
