# Spec 009: Autonomous Build System

## Feature: Self-building agent loop that implements Holus feature-by-feature via scheduled Claude Code sessions

### Overview

The autonomous build system runs Claude Code sessions every 30 minutes via macOS launchd. Each session reads the priority queue (`.self-improvement/NEXT.md`), picks the top unfinished task, implements it, runs tests, commits, and updates the queue. After 24 hours (~48 cycles), Holus should have a functional marketing agent that can observe analytics, create content, and post to social media. This is the "meta-system" that builds all other features.

### User Stories

- As a founder, I want to set up a cron that runs Claude Code every 30 minutes so that Holus builds itself while I sleep.
- As a founder, I want each build session to pick the highest-priority unfinished task so that work progresses in the right order.
- As a founder, I want the build system to run `just check` before committing so that broken code never lands on main.
- As a founder, I want a kill switch to stop all build sessions if something goes wrong.

---

### Core Specifications

**SPEC-001: Builder Agent Definition**

| Field | Value |
|-------|-------|
| Description | Claude Code agent (``.claude/agents/builder.md``) that reads NEXT.md, picks the top P0 task, implements it, tests it, and commits |
| Trigger | launchd runs `just build-cycle` every 30 minutes |
| Input | `.self-improvement/NEXT.md` (priority queue), relevant spec files, existing codebase |
| Output | Implemented code, passing tests, git commit, updated NEXT.md |
| Validation | `just check` must pass before committing. No force-pushes. |
| Auth Required | No (runs locally) |

The builder agent follows this loop:

```
1. READ .self-improvement/NEXT.md
2. FIND the first unchecked [ ] task in the highest priority group (P0 first)
3. READ the relevant spec for that task
4. IMPLEMENT the task (write code, create tests)
5. RUN `just check` (lint + typecheck + tests)
6. IF check passes:
   - Git commit with descriptive message
   - Mark task as [x] in NEXT.md
   - Log what was done to .self-improvement/memory/trajectory.jsonl
7. IF check fails:
   - Fix the issues
   - Retry `just check`
   - If still failing after 2 attempts, leave task unchecked, add a note, move to next task
8. EXIT
```

Acceptance Criteria:
- [ ] `.claude/agents/builder.md` agent definition exists and works with `claude --agent`
- [ ] Agent reads NEXT.md and correctly identifies the top priority task
- [ ] Agent reads the relevant spec before implementing
- [ ] `just check` runs and passes before any commit
- [ ] Agent commits with descriptive messages
- [ ] Agent marks completed tasks in NEXT.md
- [ ] Agent logs to trajectory.jsonl

---

**SPEC-002: launchd Scheduler**

| Field | Value |
|-------|-------|
| Description | macOS launchd plist that runs the builder agent every 30 minutes |
| Trigger | System timer (every 1800 seconds) |
| Input | None |
| Output | Claude Code session output in logs/ |
| Validation | launchd reports agent as loaded and running |
| Auth Required | No |

```xml
<!-- infra/launchd/com.holus.builder.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.holus.builder</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd /Users/mini/.openclaw/workspace/github/holus && just build-cycle</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/mini/.openclaw/workspace/github/holus</string>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>StandardOutPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/builder.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/builder.stderr.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Justfile commands:

```just
# Run one build cycle (called by launchd or manually)
build-cycle:
    claude --agent .claude/agents/builder.md --print

# Install the launchd scheduler
schedule-builder:
    mkdir -p logs
    cp infra/launchd/com.holus.builder.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/com.holus.builder.plist
    @echo "Builder scheduled every 30 minutes. Check logs/builder.*.log"

# Stop the scheduler
unschedule-builder:
    launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist
    @echo "Builder unscheduled."

# Check builder status
builder-status:
    launchctl list | grep holus || echo "No holus agents scheduled"
    @echo "---"
    @tail -20 logs/builder.stdout.log 2>/dev/null || echo "No logs yet"
```

Acceptance Criteria:
- [ ] `infra/launchd/com.holus.builder.plist` exists with correct paths
- [ ] `just schedule-builder` installs and loads the launchd agent
- [ ] `just unschedule-builder` removes the launchd agent
- [ ] `just build-cycle` runs one build session manually
- [ ] `just builder-status` shows whether the builder is running and recent logs
- [ ] Logs are written to `logs/builder.stdout.log` and `logs/builder.stderr.log`
- [ ] launchd does not start a new session if the previous one is still running

---

**SPEC-003: Run Lock (Overlap Prevention)**

| Field | Value |
|-------|-------|
| Description | File-based lock that prevents overlapping build sessions |
| Trigger | Start of every build cycle |
| Input | Agent name |
| Output | Lock file in /tmp/holus/ |
| Validation | Only one session runs at a time |
| Auth Required | No |

```python
# src/holus/core/run_lock.py
from __future__ import annotations

import fcntl
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


@contextmanager
def acquire_run_lock(
    agent_name: str,
    lock_dir: Path = Path("/tmp/holus"),
) -> Generator[None, None, None]:
    """Prevent overlapping runs of the same agent.

    Uses OS-level flock which auto-releases on crash.
    """
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{agent_name}.lock"

    fd = open(lock_file, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"Agent {agent_name} is already running. Exiting.", file=sys.stderr)
        fd.close()
        sys.exit(0)

    try:
        fd.write(str(os.getpid()))
        fd.flush()
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        lock_file.unlink(missing_ok=True)
```

Acceptance Criteria:
- [ ] `acquire_run_lock("builder")` prevents a second instance from running
- [ ] Lock is automatically released if the process crashes (flock guarantee)
- [ ] Second instance exits cleanly with message, not with an error
- [ ] Lock file is cleaned up after normal exit

---

**SPEC-004: Build Session Logging**

| Field | Value |
|-------|-------|
| Description | Each build session logs what it did to trajectory.jsonl for the manager to review |
| Trigger | End of each build cycle |
| Input | What task was picked, what was implemented, whether tests passed |
| Output | Append to `.self-improvement/memory/trajectory.jsonl` |
| Validation | Entry must have valid JSON schema |
| Auth Required | No |

```json
{
  "agent_id": "builder",
  "timestamp": "2026-02-26T10:30:00Z",
  "task_type": "build_cycle",
  "task_picked": "Implement marketing agent ReAct loop",
  "spec_reference": "specs/010-marketing-agent.md",
  "status": "success",
  "files_changed": ["src/holus/agents/marketing/agent.py", "tests/unit/agents/test_marketing.py"],
  "tests_passed": true,
  "commit_hash": "abc1234",
  "duration_seconds": 420,
  "notes": "Implemented observe and reason stages. Act stage deferred to next cycle."
}
```

Acceptance Criteria:
- [ ] Every build session appends exactly one entry to trajectory.jsonl
- [ ] Failed sessions are logged with `status: "error"` and error details
- [ ] Skipped sessions (lock conflict) are logged with `status: "skipped"`

---

### Data Structures

```python
# Build session result
from pydantic import BaseModel
from datetime import datetime

class BuildCycleResult(BaseModel):
    agent_id: str = "builder"
    timestamp: datetime
    task_type: str = "build_cycle"
    task_picked: str
    spec_reference: str | None = None
    status: str  # "success" | "error" | "skipped" | "tests_failed"
    files_changed: list[str] = []
    tests_passed: bool | None = None
    commit_hash: str | None = None
    duration_seconds: float
    notes: str = ""
    error_message: str | None = None
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `.claude/agents/builder.md` | New | Builder agent definition |
| `infra/launchd/com.holus.builder.plist` | New | launchd scheduler |
| `src/holus/core/run_lock.py` | New | Run lock for overlap prevention |
| `justfile` | Modified | Add build-cycle, schedule-builder, unschedule-builder commands |
| `logs/` | New (gitignored) | Build session logs |

---

### Edge Cases & Error Handling

**EDGE-001: Build session takes longer than 30 minutes**
- Scenario: A complex task takes 45 minutes to implement
- Expected behavior: launchd triggers the next session, but the run lock prevents overlap. The second session exits immediately with "already running" message.
- Recovery: Automatic. The next session after the current one finishes will pick up the next task.

**EDGE-002: All P0 tasks are done**
- Scenario: Builder finishes all P0 tasks and needs to move to P1
- Expected behavior: Builder reads NEXT.md top-to-bottom and picks the first unchecked task regardless of priority level.
- Recovery: Automatic priority progression.

**EDGE-003: Tests fail and cannot be fixed**
- Scenario: Builder implements code but tests fail. Two fix attempts also fail.
- Expected behavior: Builder leaves the task unchecked, adds a `⚠️ blocked:` note to the task in NEXT.md, moves to the next task.
- Recovery: Human reviews the blocked task and either fixes it or provides guidance.

**EDGE-004: Claude Code API unavailable**
- Scenario: Anthropic API is down or rate-limited
- Expected behavior: Build session logs the error and exits. Next session retries.
- Recovery: Automatic on next cycle.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Average build cycle | 10-25 min | trajectory.jsonl duration_seconds |
| Tasks completed per day | 20-40 | Count successful entries in trajectory.jsonl |
| Test pass rate | > 90% | Count tests_passed: true / total |
| Time to functional agent | < 24 hours | First successful content post |

---

### Security Considerations

- Builder agent runs with the same permissions as the user. No privilege escalation.
- Builder never force-pushes or modifies config/guardrails.yaml.
- Builder never exposes secrets in commits (pre-commit hook enforces this).
- Builder logs are gitignored (may contain API responses).

---

### Out of Scope

- Remote execution (this runs locally on macOS only)
- Multi-machine coordination (single Mac Mini)
- Cloud CI/CD integration (that's a separate spec)

---

### Related Specs

- [010-marketing-agent.md](./010-marketing-agent.md) — primary feature the builder will implement first
- [013-scheduling-runtime.md](./013-scheduling-runtime.md) — the runtime scheduling that Holus itself uses (separate from build scheduling)

---

**Last Updated:** 2026-02-26
**Status:** Not Started
**Owner:** Camilo Martinez
