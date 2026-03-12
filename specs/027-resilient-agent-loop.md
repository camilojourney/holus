# Spec 027 — Resilient Agent Loop

**Status:** In Progress
**Author:** Claude Sonnet 4.6
**Created:** 2026-03-12

---

## Problem

The current agent loop lacks a formal state machine. When failures occur mid-cycle
(LLM timeout, MCP silo unreachable, content quality failure), the agent either
crashes silently or leaves partial work with no recovery path. Trajectory logs
are written inconsistently — missing on failure paths.

This means:
- No visibility into which phase failed and why
- No ability to resume a partially completed cycle
- Health preflight exists but doesn't gate the loop
- Trajectory entries missing for failed cycles → gaps in the self-improvement data

---

## Solution

Add a **CycleState machine** that tracks every phase transition, a **health preflight**
that gates the loop before any work starts, and a **trajectory contract** that ensures
every cycle — success or failure — writes a complete entry.

---

## Architecture

### State Machine Flow

```
STARTING → HEALTH_CHECK → LOADING_STATE → OBSERVING → REASONING
         → CREATING → QUALITY_CHECK → POSTING → IMPROVING → SAVING_STATE → DONE
                                     ↘ any state can transition to FAILED
```

All transitions are logged to `trajectory.jsonl` with phase + timestamp.

### Blocking vs Non-Blocking Checks

| Check | Blocking | Reason |
|-------|----------|--------|
| Kill switch active | Yes | Safety-critical |
| LLM (Anthropic API) reachable | Yes | Can't reason without LLM |
| Social Media MCP | Yes | Primary output channel |
| Pilaster MCP | No | Image generation — fallback exists |
| Genpeli MCP | No | Video generation — fallback exists |
| Trajectory log writable | Yes | Data integrity |
| Run lock (no concurrent run) | Yes | Prevents double-posting |

---

## Components

### 1. `src/holus/core/cycle_state.py`

```python
class CycleState(StrEnum):
    STARTING = "starting"
    HEALTH_CHECK = "health_check"
    LOADING_STATE = "loading_state"
    OBSERVING = "observing"
    REASONING = "reasoning"
    CREATING = "creating"
    QUALITY_CHECK = "quality_check"
    POSTING = "posting"
    IMPROVING = "improving"
    SAVING_STATE = "saving_state"
    DONE = "done"
    FAILED = "failed"
```

`CycleContext` dataclass:
- `cycle_id: str` — ISO timestamp string (e.g. `"2026-03-12T14:30:00Z"`)
- `current_state: CycleState`
- `health_result: HealthResult | None`
- `content_created: int` — count of content items created
- `content_posted: int` — count of content items posted successfully
- `content_failed: int` — count of content items that failed
- `quality_scores: list[float]` — per-item quality scores (0.0–1.0)
- `capability_gaps: list[str]` — skills/tools that were missing
- `error: str | None` — error message if FAILED
- `duration_seconds: float | None` — set on DONE or FAILED
- `started_at: datetime`

`transition(new_state: CycleState)` method: logs to `trajectory.jsonl` with
`{"cycle_id": ..., "phase": ..., "timestamp": ..., "from_state": ...}`.

### 2. `src/holus/core/health.py` — `run_preflight_checks()` function

Returns `HealthResult(blocking_ok: bool, available_silos: list[str], warnings: list[str])`.

Check order:
1. Kill switch — blocking
2. LLM reachable (HEAD to Anthropic API) — blocking
3. Social Media MCP — blocking
4. Pilaster MCP — non-blocking (add warning, remove from available_silos)
5. Genpeli MCP — non-blocking (add warning, remove from available_silos)
6. Trajectory log writable — blocking
7. Run lock — blocking

### 3. Trajectory Contract

Function `write_trajectory_entry(context: CycleContext)` in `cycle_state.py`:

```json
{
  "cycle_id": "2026-03-12T14:30:00Z",
  "phase": "done",
  "health": {"blocking_ok": true, "available_silos": ["social_media"], "warnings": []},
  "content_created": 2,
  "content_posted": 2,
  "content_failed": 0,
  "quality_scores": [0.87, 0.92],
  "capability_gaps": [],
  "duration_seconds": 142.3,
  "error": null
}
```

Written to `.self-improvement/memory/trajectory.jsonl` — appended, never overwritten.
Written at `DONE` and `FAILED` states. Created directory if missing.

---

## Files Modified / Created

| File | Action |
|------|--------|
| `src/holus/core/cycle_state.py` | Create |
| `src/holus/core/health.py` | Add `run_preflight_checks()`, `HealthResult` |
| `src/holus/core/__init__.py` | Export new types |
| `tests/unit/core/test_cycle_state.py` | Create |
| `tests/unit/core/test_health_preflight.py` | Create |

---

## Test Coverage Requirements

- `CycleState` enum has all 12 states
- `CycleContext.transition()` appends to trajectory.jsonl
- `CycleContext.transition()` updates `current_state`
- `write_trajectory_entry()` writes correct JSON format
- `write_trajectory_entry()` creates directory if missing
- `run_preflight_checks()` returns `blocking_ok=False` when kill switch active
- `run_preflight_checks()` returns warnings for non-blocking failures
- `run_preflight_checks()` removes failed silo from available_silos

---

## Cycle Plan

- **Cycle 1** (this spec): CycleState machine + health preflight + trajectory contract
- **Cycle 2**: Wire CycleContext into the marketing agent loop
- **Cycle 3**: Add resume logic for interrupted cycles

---

## Non-Goals

- Not replacing the existing `HealthCheck` class (it stays for monitoring)
- Not implementing resume logic in this cycle
- Not changing the marketing agent loop structure yet (Cycle 2)
