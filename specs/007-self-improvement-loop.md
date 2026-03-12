# Spec 007: Self-Improvement Loop

**Status:** Not Started
**Phase:** Phase 3 (requires Phase 1 content production working first)
**Author:** Juan + Opus
**Created:** 2026-03-12
**Updated:** 2026-03-12

## Problem

The marketing agent can only use capabilities hardcoded at build time. When it
encounters a gap — "I should make carousels but I can't" — it logs it and moves on.
The human has to notice, spec it, code it, and deploy it. The agent can never evolve
faster than the human can code.

But the agent already lives inside the same system that builds things. The doctrine
pipeline (`/research` → `/specs` → `/code` → `/verify`) runs via CLI. Codex writes
code. The agent can invoke these tools. It just doesn't know it can.

## Goals

- Agent identifies capability gaps during REASON phase (strategy, not exception handling)
- Agent handles simple gaps itself (write a YAML config, use it immediately)
- Agent files build requests for complex gaps (code gets built between content cycles)
- Content creation is ALWAYS primary — building never blocks or delays content
- Kill switch pauses builds instantly if the agent is looping instead of producing
- Budget caps prevent runaway spending on builds
- Forbidden targets prevent the agent from modifying its own core, guardrails, or auth

## Non-Goals

- Agent modifying its own core loop, kill switch, or guardrails — NEVER
- Agent building in other repos (pilaster, genpeli, social-media) — those are silos
- Agent optimizing its own prompts — that's prompt_optimizer.py (already built)
- Full recursive self-improvement — scoped to content capabilities only

## Solution

### The Core Idea

Self-improvement is not a separate system bolted onto the agent. It's part of how
the agent thinks. During REASON, the agent considers what capabilities it has AND
what capabilities it wishes it had. When it identifies a gap, it decides:

1. **Work around it** — use existing tools creatively (preferred)
2. **Fix it now** — write a YAML config (specialist, reviewer, prompt template)
3. **Request a build** — file a structured request, Codex builds it on a branch
4. **Escalate to human** — structural change that needs a spec and human judgment

The agent ALWAYS continues producing content with what it has. Building never
blocks content production. A build request is a side-effect of REASON, not the
main output.

### How It Works

```
CONTENT CYCLE (every 30 min)
  OBSERVE → REASON → CREATE → EVALUATE → POST
                |
                ↓
         "What do I need that I don't have?"
                |
         ┌──────┼──────────┼──────────┐
      nothing  config    code     architecture
         |    change    change     change
         |      |         |           |
      continue  write    file       file
               YAML    request    request
              (now)   (Codex     (human
                       builds    reviews)
                       between
                       cycles)

  ─── after POST ───
  Check: pending build request + budget OK + not paused?
    → YES: run ONE build via Codex on a feature branch
    → NO: skip, try next cycle
```

### What the Agent Can Create Directly (Config)

When the gap is just a missing config, the agent writes it inline. No build
pipeline, no branch, no review. Available immediately.

**Can create:**
- Specialist YAML in `config/specialists/spawned/`
- Reviewer YAML in `config/reviewers/spawned/`
- Prompt templates in `config/prompts/`

**Cannot create:**
- Python code (needs build request)
- Modifications to existing configs (only new files)
- Anything in `src/`

**Safety net:** Bad config → bad content → quality gate (quality_score.py + reviewer
pool) catches it → content doesn't get posted. The quality gate IS the safety net
for config changes.

### What Gets Built via Codex (Code)

When the gap needs Python code, the agent files a build request:

```yaml
# .self-improvement/capability-requests/YYYY-MM-DD-{slug}.yaml
what: "Carousel content adapter for Instagram"
why: "Tutorials get 4x engagement as carousels vs single images"
evidence: "Top 3 competitors use carousels"
workaround: "Single image with text overlay — 60% lower engagement"
status: pending  # pending → building → built → merged | failed
branch: null
```

After the content cycle completes, if there's a pending request and budget allows,
the agent invokes Codex to build it:

```
codex exec "Implement {what} in the holus repo. Create on branch feat/self-built-{slug}.
Write tests. Run just check. Commit."
```

Codex builds on a feature branch. Tests must pass. The branch sits there until
the human merges it. The agent doesn't merge its own builds.

**Safety net:** Feature branch + tests + human merge review. If the build fails
tests, it's marked as failed. After 3 consecutive failures, builds auto-pause.

### What Needs a Human (Architecture)

When the gap is structural — a new silo integration, a new agent type, a schema
change — the agent files a request and waits. It notifies via macOS notification
and logs to trajectory.

The human reviews, runs `/specs holus` + `/code holus` to build it, and marks
the request as resolved.

### Guardrails

```yaml
# config/guardrails.yaml (new section)
self_improvement:
  enabled: true
  max_builds_per_day: 2
  max_builds_per_week: 5
  max_cost_per_build_usd: 5.00
  max_cost_per_week_usd: 20.00
  max_build_duration_minutes: 30
```

**Forbidden targets** — the agent can NEVER modify these, enforced by path check:
- `content_loop.py`, `build_dispatch.py`, `kill_switch.py` (its own machinery)
- `config/guardrails.yaml` (its own constraints)
- Any file with "auth", "secret", "key" in the path
- `src/holus/core/mcp/` (silo contracts affect other repos)

**Kill switch states:**
- `ACTIVE` — everything runs
- `BUILD_PAUSED` — content continues, builds stopped
- `ALL_PAUSED` — everything stopped

**Auto-pause triggers:**
- 3 consecutive build failures
- Weekly budget exceeded
- 3 builds this week, 0 content used any of them
- Any attempt to touch a forbidden target (this is a bug — alert immediately)

### Notification

Available now: macOS notifications (`osascript -e 'display notification'`),
Gmail MCP (draft to self). Telegram bot is not built yet (Spec 013, partial).

Notify on: build started, build completed, build failed, auto-paused, forbidden
target attempt.

## Implementation Notes

### Phase 1: Gap Detection in REASON
1. Update REASON prompt to include capability awareness
2. Agent reads `config/` directory to know what exists
3. Structured output: `content_decisions[]` + `capability_gaps[]`
4. Each gap classified as config/code/architecture
5. Tests: verify gap classification logic

### Phase 2: Config Self-Creation
1. Agent writes specialist/reviewer/prompt YAMLs during ACT phase
2. New configs go to `spawned/` subdirectories
3. Quality gate validates content from new configs
4. Tests: YAML creation, quality gate catches bad configs

### Phase 3: Build Dispatch
1. Build request YAML persistence in `.self-improvement/capability-requests/`
2. After content cycle: check for pending requests, invoke Codex if budget allows
3. One build per cycle maximum. Feature branch. Tests must pass.
4. `just build-capabilities` for manual trigger
5. Tests: budget enforcement, kill switch, forbidden targets

### Phase 4: Kill Switch + Guardrails
1. Add `BUILD_PAUSED` state to `kill_switch.py`
2. Add `self_improvement` section to `config/guardrails.yaml`
3. Path-based enforcement of forbidden targets
4. Auto-pause on 3 consecutive failures
5. Usage tracking: builds/week, features-used rate

### Dependencies

- Depends on: Spec 010 (marketing agent — implemented)
- Depends on: Spec 025 (content loop — needs REASON phase structured output)
- Depends on: Spec 008 (kill switch — needs BUILD_PAUSED state)
- Depends on: Working Codex CLI (`codex exec`)
- Depended on by: Spec 006 (coordinator, Phase 3)

## Alternatives Considered

### Alternative A: Separate Build Agent

Run a dedicated "builder agent" as its own process/cron that watches for requests.
Rejected because: adds process management complexity for no benefit. The content
agent can invoke Codex directly after its cycle. Same result, simpler system.

### Alternative B: Agent Uses Full Skill Pipeline (/specs → /code → /verify)

Agent shells out to `claude -p` to run the full doctrine pipeline for each build.
Rejected because: `claude -p` stalls with 0-byte output (known issue). Codex is
reliable for code changes. The full pipeline is overkill for adding a content
adapter — that's a single-file code change, not a multi-phase project.

### Alternative C: Human Approves Every Build

Every build request goes to human before execution.
Rejected because: defeats autonomous improvement. Compromise: human reviews the
BRANCH after build, not before. Budget caps and kill switch prevent runaway.

## Edge Cases & Failure Modes

- **Request flood:** Budget caps stop builds at 2/day. Requests queue by priority.
- **Build breaks tests:** Marked "failed", failure count increments, auto-pause at 3.
- **Build succeeds but unused:** 3 builds + 0 content using them = auto-pause + notify.
- **Recursive build attempt:** "Improve the build system" blocked by forbidden targets.
- **Budget exhaustion mid-week:** No builds until next week. Content continues normally.
- **Kill switch during build:** Process killed. Request marked "killed". Branch partial.
  Clean state — nothing merged to main.
- **Codex unavailable:** Build dispatch detects missing CLI, marks request "blocked",
  notifies human. Does not fall back to `claude -p` (stall risk).

## Observability

- Trajectory logging: every build attempt in trajectory.jsonl
- macOS notifications: build complete/fail/auto-pause
- Langfuse tracing: build pipeline invocations
- Weekly summary: builds attempted, succeeded, features used in content

## Rollback Plan

- Every build is on a feature branch — delete the branch to undo
- Config changes: delete the YAML file from `spawned/` directory
- Kill switch: `BUILD_PAUSED` stops all future builds instantly
- Nuclear: `self_improvement.enabled: false` in guardrails.yaml

## Open Questions

- [ ] Should built features go through a "probation" period on test accounts? — @Juan
- [ ] Should the build dispatch run as part of the content cycle or as a separate
      just command triggered by cron? — @Juan

## Acceptance Criteria

- [ ] REASON phase outputs `capability_gaps[]` alongside content decisions
- [ ] Agent writes specialist/reviewer YAMLs directly for config gaps
- [ ] Build requests persisted as YAML in `.self-improvement/capability-requests/`
- [ ] Codex invoked for code gaps, builds on feature branch, tests pass
- [ ] Kill switch `BUILD_PAUSED` stops builds but not content
- [ ] Budget enforced: max 2/day, $20/week
- [ ] Forbidden targets blocked: core loop, kill switch, guardrails, auth, silo contracts
- [ ] 3 consecutive failures auto-pause builds
- [ ] Build attempts logged to trajectory.jsonl
- [ ] Notification sent on build complete/fail/auto-pause
- [ ] Built capabilities usable in next content cycle
