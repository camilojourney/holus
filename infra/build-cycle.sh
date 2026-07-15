#!/bin/bash
# =============================================================================
# Holus Build Cycle - ONE autonomous cycle
#
# Designed to run via launchd cron (every 20-30 min) or manually.
# Each cycle picks one task from NEXT.md, implements it, and logs everything.
#
# Memory between cycles is maintained through:
#   - agentic/memory/NEXT.md          (task queue - what's done, what's next)
#   - .self-improvement/memory/trajectory.jsonl  (full history of every cycle)
#   - agentic/memory/MEMORY.md        (accumulated learnings)
#   - .self-improvement/reports/builder/  (detailed cycle reports)
#   - .self-improvement/sprint-state.json (cycle counter, auto-stop)
#
# Usage:
#   just build-cycle           # Run one cycle
#   just sprint-start          # Install launchd cron (every 20 min, 80 cycles)
#   just sprint-stop           # Uninstall the cron
#   touch /tmp/holus-stop      # Emergency stop from anywhere
#
# =============================================================================

set -euo pipefail

HOLUS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HOLUS_DIR"

# Set PATH directly (don't source .zshrc - it hangs in non-interactive mode)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
export HOME="${HOME:-/Users/mini}"
# Allow claude to run even if called from inside another claude session (e.g. testing)
unset CLAUDECODE 2>/dev/null || true

LOG_DIR="$HOLUS_DIR/logs"
mkdir -p "$LOG_DIR"

STATE_FILE="$HOLUS_DIR/.self-improvement/sprint-state.json"
KILL_FILE="/tmp/holus-stop"
LOCK_DIR="/tmp/holus-builder-cycle.lock"

# ---- Helpers ----------------------------------------------------------------

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/sprint.log"
}

get_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo '{"cycle": 0, "max_cycles": 80, "started_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'", "status": "running"}'
    fi
}

get_cycle() {
    get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('cycle', 0))"
}

get_max_cycles() {
    get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('max_cycles', 80))"
}

update_state() {
    local cycle="$1"
    local status="$2"
    python3 -c "
import json, sys
from datetime import datetime, timezone
try:
    state = json.load(open('$STATE_FILE'))
except:
    state = {}
state['cycle'] = $cycle
state['status'] = '$status'
state['last_cycle_at'] = datetime.now(timezone.utc).isoformat()
if 'started_at' not in state:
    state['started_at'] = datetime.now(timezone.utc).isoformat()
if 'max_cycles' not in state:
    state['max_cycles'] = 80
json.dump(state, open('$STATE_FILE', 'w'), indent=2)
"
}

# Generate a context summary from recent trajectory for the agent
generate_memory_context() {
    python3 << 'PYEOF'
import json
from pathlib import Path

trajectory = Path(".self-improvement/memory/trajectory.jsonl")
reports_dir = Path(".self-improvement/reports/builder")

lines = []
if trajectory.exists():
    lines = [l.strip() for l in trajectory.read_text().splitlines() if l.strip()]

# Last 5 entries from trajectory
recent = lines[-5:] if len(lines) > 5 else lines
completed_count = len(lines)

print(f"## Memory Context (auto-generated)")
print(f"")
print(f"You have completed {completed_count} cycles so far.")
print(f"")

if recent:
    print(f"### Last {len(recent)} cycles:")
    for entry_str in recent:
        try:
            entry = json.loads(entry_str)
            task = entry.get("task_picked", "unknown")
            status = entry.get("status", "unknown")
            classification = entry.get("task_classification", "?")
            tools = entry.get("tools_used", [])
            tools_failed = entry.get("tools_failed", [])
            print(f"- [{classification}] {task} -> {status} (tools: {', '.join(tools)})")
            if tools_failed:
                print(f"  WARNING: These tools failed: {', '.join(tools_failed)}")
        except json.JSONDecodeError:
            pass
    print()

# Check for recent reports
if reports_dir.exists():
    report_files = sorted(reports_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:3]
    if report_files:
        print("### Recent reports (read for details):")
        for rf in report_files:
            print(f"- {rf}")
        print()

# Summary of what's done in NEXT.md
next_file = Path("agentic/memory/NEXT.md")
if next_file.exists():
    content = next_file.read_text()
    done = content.count("- [x]")
    remaining = content.count("- [ ]")
    print(f"### Task queue: {done} completed, {remaining} remaining")
PYEOF
}

# Cleanup lock on exit (even on crash)
cleanup() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

# ---- Guards -----------------------------------------------------------------

# Kill file check
if [ -f "$KILL_FILE" ]; then
    log "Kill file detected. Skipping cycle. Remove $KILL_FILE to resume."
    exit 0
fi

# Cycle limit check
CURRENT_CYCLE=$(get_cycle)
MAX_CYCLES=$(get_max_cycles)

if [ "$CURRENT_CYCLE" -ge "$MAX_CYCLES" ]; then
    log "Sprint complete ($CURRENT_CYCLE/$MAX_CYCLES cycles). Uninstalling cron."
    update_state "$CURRENT_CYCLE" "completed"
    launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist 2>/dev/null || true
    exit 0
fi

# No remaining tasks check
REMAINING=$(grep -c '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
if [ "$REMAINING" -eq 0 ]; then
    log "All tasks completed! Sprint finished after $CURRENT_CYCLE cycles."
    update_state "$CURRENT_CYCLE" "all_tasks_done"
    launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist 2>/dev/null || true
    exit 0
fi

# Run lock - mkdir is atomic on POSIX, works on macOS (no flock needed)
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    # Check if the lock is stale (older than 60 min = stuck cycle)
    if [ -d "$LOCK_DIR" ]; then
        LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
        if [ "$LOCK_AGE" -gt 3600 ]; then
            log "Stale lock detected (${LOCK_AGE}s old). Cleaning up."
            rmdir "$LOCK_DIR" 2>/dev/null || true
            mkdir "$LOCK_DIR" 2>/dev/null || true
        else
            log "Previous cycle still running (${LOCK_AGE}s). Skipping this tick."
            exit 0
        fi
    fi
fi

# ---- Run Cycle --------------------------------------------------------------

NEXT_CYCLE=$((CURRENT_CYCLE + 1))
NEXT_TASK=$(grep -m1 '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null | sed 's/^- \[ \] //' || echo "unknown")
CYCLE_LOG="$LOG_DIR/cycle-$NEXT_CYCLE.log"
TODAY=$(date +%Y-%m-%d)

log "===== Cycle $NEXT_CYCLE/$MAX_CYCLES | $REMAINING tasks remaining | Next: $NEXT_TASK ====="

# Generate memory context
MEMORY_CONTEXT=$(generate_memory_context 2>/dev/null || echo "No memory context available.")

START_TIME=$(date +%s)

# Pipe the prompt via heredoc to claude -p
cat <<PROMPT | claude -p \
    --max-turns 75 \
    --allowedTools "Bash(just *),Bash(pytest *),Bash(ruff *),Bash(mypy *),Bash(git add *),Bash(git commit *),Bash(git status),Bash(git diff *),Bash(git log *),Bash(ls *),Bash(mkdir *),Bash(codex *),Bash(gemini *),Bash(cat /tmp/*),Bash(touch *),Bash(chmod *),Bash(cp *),Bash(python3 *),Read,Write,Edit,Glob,Grep,TodoWrite,WebSearch,WebFetch" \
    >> "$CYCLE_LOG" 2>&1 || true
You are the Holus builder-manager, cycle $NEXT_CYCLE of $MAX_CYCLES.

READ YOUR FULL INSTRUCTIONS: .claude/agents/builder.md

$MEMORY_CONTEXT

YOUR TASK THIS CYCLE:
Pick the FIRST unchecked [ ] task from agentic/memory/NEXT.md.
Classify it (BUILD/RESEARCH/INTEGRATE/REVIEW/CREATE) and execute using the right tools.

MEMORY FILES (read these to understand past work):
- agentic/memory/MEMORY.md - accumulated learnings
- .self-improvement/memory/trajectory.jsonl - full history (read last 10 entries)
- .self-improvement/reports/builder/ - detailed reports from past cycles

AFTER COMPLETING THE TASK:
1. Run \`just check\` if code was written
2. Commit if tests pass: git add + git commit
3. Mark the task as [x] in NEXT.md
4. Write cycle report to .self-improvement/reports/builder/${TODAY}-cycle-${NEXT_CYCLE}.md
5. Append to .self-improvement/memory/trajectory.jsonl
6. If you learned something important, update agentic/memory/MEMORY.md
7. If you discovered new work needed, ADD new tasks to NEXT.md

If Codex or Gemini are unavailable, do the work yourself with Claude tools. Always report tool failures.
PROMPT

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

log "Cycle $NEXT_CYCLE completed in ${DURATION}s ($((DURATION / 60))m $((DURATION % 60))s)"

# Update sprint state
update_state "$NEXT_CYCLE" "running"

# Summary
COMPLETED=$(grep -c '^\- \[x\]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
REMAINING=$(grep -c '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
log "Progress: $COMPLETED done, $REMAINING remaining"
