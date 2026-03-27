# Plan: Holus Megasprint — Maximum Parallelism, Every File Audited

**CID:** PLAN-20260326-383e52d9 | **Repo:** holus | **Created:** 2026-03-26
**Status:** PENDING

## Goal

In 1 hour, take Holus from 75% to 95%+ by launching waves of tiny, hyper-focused agents. Every single file in the codebase gets audited for purpose and connectivity. Every gap gets attacked. Every untested module gets covered. Every partial spec gets completed.

**Key principle:** Each agent sees 3-5 files MAX. It answers one question or fixes one thing. No agent thinks about the whole system.

## Phases

### Phase 1: COHERENCE AUDIT (15 min) — 40 parallel agents
**Goal:** Every file in the codebase is audited for purpose, connectivity, and quality.
**Skills:** `/research holus` x40 (lightweight — read files, report findings)
**Done when:** We have a complete map of dead code, orphaned modules, broken imports, missing connections, and files without purpose.

40 auditor agents, each assigned a cluster of 3-5 files:
- 28 clusters cover all 130 Python source files
- 5 clusters cover all 46 agent prompt files
- 4 clusters cover all 41 frontend files
- 3 clusters cover config + docs + data

Each auditor answers:
1. Does this file have a clear purpose?
2. Is it imported/used by anything? (or does anything import it?)
3. Are its imports valid — do the things it imports actually exist?
4. Is it a stub (skeleton with no real logic) or substantial?
5. Does it connect properly to its neighbors in the architecture?
6. Any dead code, unused functions, or commented-out blocks?

**Output:** `results/phase-01-coherence-audit.md` — full inventory with verdicts per cluster.

### Phase 2: ATTACK EVERY GAP (30 min) — 60+ parallel agents
**Goal:** Every gap found in Phase 1 + every known gap from specs gets fixed simultaneously.
**Skills:** `/code holus` x35, `/ux holus` x15, `/maintenance holus` x5, `/taste holus` x5
**Done when:** All untested modules have tests, all partial specs advance, all dead code removed, all frontend pages wired to real API, all stubs either implemented or deleted.

Split into 4 parallel tracks:

**Track A: Test Coverage (20 agents via /code)**
One agent per untested module. Each writes tests for exactly ONE file:
- orchestrator.py, content_generator.py, corpus.py, content API routes, agents API routes,
  trajectory API routes, evaluations API routes, health API routes, knowledge API routes,
  results API routes, improvement API routes, genpeli client, pilaster client, dspy_optimizer,
  revision_loop, card_generator, performance_loop, visual_pipeline, voice_pipeline, mcp/server

**Track B: Implementation (15 agents via /code)**
One agent per unfinished implementation. Each completes ONE module:
- diagnostician.py (spec 036), judge_calibration.py, bandit.py (Thompson sampling),
  performance_loop.py (48h read-back), telegram_gate.py (approval webhook),
  __main__.py CLI, visual registry (spec 034), langfuse wiring, mem0 wiring,
  GitHub Actions CI, Docker healthcheck, .env.example, preflight enhancement,
  cold-start calendar activation, seo-strategist/audience-analyst/competitive-intel agent prompts

**Track C: Frontend Wiring (15 agents via /ux)**
One agent per page. Each wires ONE page to real Observatory API:
- Dashboard, Agents, Agent Detail, Content Kanban, Evaluations Heatmap,
  Trajectory Timeline, Knowledge Browser, Health Dashboard, Results Metrics,
  Followers, Engagement, About, Content Calendar, Self-Improvement,
  Dark mode + mobile responsive audit

**Track D: Dead Code & Coherence Fixes (10 agents via /code + /maintenance)**
Based on Phase 1 findings:
- Remove orphaned files, fix broken imports, delete stubs that serve no purpose,
  consolidate duplicate logic, fix the corrupted .failed file,
  update stale playbooks, clean up empty __init__.py files,
  resolve mypy overrides for 9 legacy modules,
  fix demo-data.ts to be a proper fallback (not primary),
  update NEXT.md and sprint-state.json to reflect reality

**Internal loop:** After each track completes, run `just check`. If failures, fix agents re-run.

### Phase 3: QUALITY + SHIP (15 min) — 20 parallel agents
**Goal:** Everything reviewed, verified, taste-checked, and committed.
**Skills:** `/taste holus` x4, `/consult-engineering holus` x3, `/consult-systems holus` x2, `/verify holus` x2, `/maintenance holus` x2, `/consult-experiments holus` x1, `/consult-business` x1, `/ux holus` x2, `/code holus` x3
**Done when:** All tests pass, all pages render, taste >= 8/10, architecture reviewed, specs updated.
**Gate:** hard (approve before committing)

Quality agents (all parallel):
- `/taste` x4: brand consistency, content quality, agent prompt quality, observatory UX
- `/consult-engineering` x3: architecture review, MCP design review, testing strategy review
- `/consult-systems` x2: learning loop stability, autonomous sprint safety
- `/consult-experiments` x1: evaluator rubric design review
- `/consult-business` x1: product promotion strategy review
- `/verify` x2: acceptance criteria + frontend Playwright
- `/maintenance` x2: deps + lint + types final check
- `/ux` x2: accessibility audit + mobile responsive final pass

Integration fixers (sequential after quality):
- `/code` x3: merge conflict resolution, wire new modules into agent loop, update all spec statuses

## Agent Count Summary

| Phase | Agents | Duration | Focus |
|-------|--------|----------|-------|
| 1: Coherence Audit | 40 | ~15 min | Read every file, report purpose + connectivity |
| 2: Attack Gaps | 60 | ~30 min | Tests, implementations, frontend, dead code |
| 3: Quality + Ship | 20 | ~15 min | Review, verify, taste-check, commit |
| **TOTAL** | **120** | **~60 min** | **Every file touched, every gap attacked** |

## Risks

1. **Merge conflicts from 60 parallel agents editing code** — Phase 3 has dedicated conflict resolution agents
2. **Phase 1 findings may change Phase 2 priorities** — Phase 2 tracks are adaptive, can absorb new findings
3. **Some modules may need deletion rather than testing** — Auditors flag stubs, Phase 2 Track D handles cleanup
4. **Frontend wiring may reveal API gaps** — Phase 2 Track C agents can create API stubs if needed
5. **Token budget** — Each agent is deliberately tiny (3-5 files) to minimize per-agent cost
