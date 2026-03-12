# Spec 027: Resilient Agent Loop

**Status:** Not Started
**Phase:** Phase 0 (prerequisite for everything else)
**Author:** Juan + Fruco
**Created:** 2026-03-12

## Problem

The marketing agent runs every 30 minutes. Something WILL go wrong — API down, token expired, model error, platform rate limit. Right now the agent has no standard recovery pattern. One failure can silently stop all content production and nobody knows until they manually check.

The agent needs to be bulletproof BEFORE self-improvement (Spec 007) or any other phase makes sense.

## The 4 Phases

```
PHASE 0 — HEALTH CHECK (prerequisite, must pass before anything else)
PHASE 1 — CONTENT CREATION LOOP (primary job)
PHASE 2 — QUALITY GATE (don't post garbage)
PHASE 3 — SELF-IMPROVEMENT (get better over time)
```

Each phase gates the next. If Phase 0 fails, Phases 1-3 don't run. If Phase 2 fails, content doesn't post. Phase 3 only runs when 0-2 are stable.

---

## Phase 0 — Health Check

**Goal:** Before every cycle, verify the agent can reach everything it needs.

**Checks (in order, fail fast):**
1. Kill switch — is the agent paused?
2. LLM reachable — can we get a response from the model?
3. Social Media MCP — can we reach the publishing silo?
4. Pilaster MCP — can we reach the content/image silo? (non-blocking — log warning, continue)
5. Genpeli MCP — can we reach the video silo? (non-blocking — log warning, continue)
6. Trajectory log — can we write to it?
7. Run lock — is another instance already running?

**On failure of blocking checks (1, 2, 3, 6, 7):**
- Log to trajectory.jsonl: `{cycle_id, phase: "health", status: "failed", reason, timestamp}`
- Notify Juan via Telegram (if configured)
- Skip this cycle entirely
- Sleep until next scheduled run
- DO NOT crash — exit cleanly with code 0

**On failure of non-blocking checks (4, 5):**
- Log warning to trajectory.jsonl
- Disable that silo for this cycle only
- Continue with reduced capabilities

**Implementation:** Extend `src/holus/core/health.py` with `run_preflight_checks()` that returns `HealthResult(blocking_ok: bool, available_silos: list[str], warnings: list[str])`.

---

## Phase 1 — Content Creation Loop

**Goal:** Agent does its primary job — creates content every 30 minutes.

**The loop (each cycle is independent):**

```
1. LOAD STATE
   - Read last N entries from trajectory.jsonl
   - Determine: what was posted recently? what failed last time?
   - If last cycle failed → adjust strategy (different format, different platform)

2. OBSERVE
   - Read capabilities.yaml (what can I do?)
   - Read knowledge base (what's trending? what did competitors post?)
   - Read content queue (anything pending approval?)

3. REASON
   - Decide: what to create this cycle
   - Identify: any capability gaps? (file request, don't block)
   - Output: content_decisions[] + capability_gaps[]

4. CREATE
   - Call specialist agents per content type
   - If specialist fails → log it, try fallback format, continue
   - Never block the cycle on a single content piece

5. SAVE STATE
   - Write to trajectory.jsonl ALWAYS — success OR failure
   - This is the contract: every cycle leaves a trace
```

**Key rules:**
- Each cycle is independent — failure in cycle N doesn't affect cycle N+1
- Agent always wakes up fresh, reads trajectory, decides what to do
- Partial success is success — if 3/5 content pieces succeed, post those 3
- SAVE STATE is the last step, always executed (even in exception handlers)

---

## Phase 2 — Quality Gate

**Goal:** Don't post content that fails quality standards.

**Already exists:** `quality_score.py` + reviewer pool (Spec 026).

**What's missing:**
- Quality gate must be enforced BEFORE posting, not after
- Failed quality items must be logged to trajectory.jsonl with reason
- Retry logic: if score < 7, regenerate once with feedback, then accept or discard
- Hard block: if score < 4, discard entirely, log, move on

**Quality check flow:**
```
Content created → Quality agent scores (1-10)
  < 4 → discard, log "quality_hard_fail", continue to next piece
  4-6 → regenerate once with reviewer feedback → re-score
        if still < 6 → discard, log "quality_soft_fail"
        if ≥ 6 → accept
  ≥ 7 → accept, log "quality_pass"
  → Post accepted content
```

---

## Phase 3 — Self-Improvement

**Goal:** Agent gets better over time without human intervention.

**Status:** Already specced in detail in Spec 007 (Self-Improvement Loop).

**Prerequisite:** Phases 0-2 must be stable first.

**What Spec 007 needs updated:**
- Gap detection happens in REASON phase (Phase 1), not as a separate system
- Tier 1 (YAML config) runs inline during the current cycle
- Tier 2 (code via Codex) runs AFTER the content cycle, not during
- Tier 3 (architecture) always requires Juan

---

## The State Machine

```python
class CycleState(Enum):
    STARTING = "starting"
    HEALTH_CHECK = "health_check"       # Phase 0
    LOADING_STATE = "loading_state"     # Phase 1
    OBSERVING = "observing"             # Phase 1
    REASONING = "reasoning"             # Phase 1
    CREATING = "creating"               # Phase 1
    QUALITY_CHECK = "quality_check"     # Phase 2
    POSTING = "posting"
    IMPROVING = "improving"             # Phase 3
    SAVING_STATE = "saving_state"       # Always runs
    DONE = "done"
    FAILED = "failed"
```

Every state transition writes to trajectory.jsonl. If the agent crashes mid-cycle, the last written state tells you exactly where it stopped.

---

## Dead Man's Switch

If NO successful cycle has completed in 2 hours:
- Send Telegram alert to Juan: "Holus has not posted in 2 hours. Last error: {reason}"
- Do NOT auto-restart (could loop on a real problem)
- Wait for human to investigate or restart

This runs as a separate launchd job (`com.holus.watchdog`) every 30 minutes, independent of the main agent loop.

---

## trajectory.jsonl — The Contract

Every cycle writes at minimum:

```json
{
  "cycle_id": "2026-03-12T02:30:00Z",
  "phase": "done",
  "health": {"status": "ok", "silos_available": ["social-media", "pilaster"]},
  "content_created": 3,
  "content_posted": 3,
  "content_failed": 0,
  "quality_scores": [8.2, 7.5, 9.1],
  "capability_gaps": [],
  "duration_seconds": 47,
  "error": null
}
```

On failure:

```json
{
  "cycle_id": "2026-03-12T03:00:00Z",
  "phase": "health_check",
  "health": {"status": "failed", "reason": "social-media MCP unreachable"},
  "content_created": 0,
  "content_posted": 0,
  "error": "ConnectionError: http://localhost:8000"
}
```

---

## What Exists vs What's Needed

| Component | Exists | Needs Work |
|-----------|--------|------------|
| `core/health.py` | ✅ Basic health checks | Add `run_preflight_checks()` with silo-aware results |
| `core/kill_switch.py` | ✅ Implemented | Add `BUILD_PAUSED` state (Spec 007) |
| `core/run_lock.py` | ✅ Implemented | — |
| Marketing agent loop | ✅ Spec 010, Implemented | Wire state machine + cycle independence |
| trajectory.jsonl | ✅ Exists | Enforce write-on-every-cycle contract |
| Quality gate | ✅ quality_score.py | Enforce before post, add retry logic |
| Dead man's switch | ❌ Missing | New launchd watchdog job |
| State machine (CycleState) | ❌ Missing | New, wires all phases together |
| Telegram notifications on failure | ❌ Missing | New, uses existing MCP or direct API |

## Dependencies
- Requires: Spec 001 (core infra), Spec 010 (marketing agent), Spec 013 (scheduling)
- Blocks: Spec 007 (self-improvement — needs this stable first)
- Blocks: Spec 026 (reviewer pool — needs quality gate wired)

## Acceptance Criteria
- [ ] Every 30-min cycle writes to trajectory.jsonl regardless of outcome
- [ ] Phase 0 failure skips cycle cleanly, logs reason, notifies Juan
- [ ] Non-blocking silo failures degrade gracefully (agent continues without that silo)
- [ ] Quality gate runs before every post — hard fails discarded, soft fails get one retry
- [ ] Dead man's switch alerts after 2h of no successful cycles
- [ ] State machine logs every phase transition
- [ ] 3 consecutive cycle failures → Telegram alert + BUILD_PAUSED
- [ ] `python -m holus health` shows current phase status for all 4 phases
