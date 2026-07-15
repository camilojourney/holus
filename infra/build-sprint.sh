#!/bin/bash
# =============================================================================
# Holus Autonomous Build Sprint - LOOP MODE
#
# Runs build-cycle.sh in a loop with cooldown between cycles.
# Alternative to the cron-based approach (just sprint-start).
#
# Usage:
#   just sprint-loop             # Start loop (80 cycles)
#   just sprint-loop 40          # Override cycle count
#   just sprint-stop             # Stop gracefully
#   touch /tmp/holus-stop        # Emergency stop
#
# Monitor:
#   just sprint-status           # Full dashboard
#   tail -f logs/sprint.log      # Live progress
# =============================================================================

set -euo pipefail

HOLUS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HOLUS_DIR"

LOG_DIR="$HOLUS_DIR/logs"
mkdir -p "$LOG_DIR"

KILL_FILE="/tmp/holus-stop"
MAX_CYCLES=${1:-80}
COOLDOWN=120  # seconds between cycles

# Reset sprint state for loop mode
python3 -c "
import json
from datetime import datetime, timezone
json.dump({
    'cycle': 0,
    'max_cycles': $MAX_CYCLES,
    'status': 'running',
    'started_at': datetime.now(timezone.utc).isoformat(),
    'mode': 'loop',
    'interval_minutes': 2
}, open('agentic/sprint-state.json', 'w'), indent=2)
"

# Clean up kill file from previous runs
rm -f "$KILL_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/sprint.log"
}

log "========================================="
log "Holus Build Sprint started (loop mode)"
log "Max cycles: $MAX_CYCLES"
log "Cooldown: ${COOLDOWN}s between cycles"
log "Kill file: $KILL_FILE"
log "========================================="

CYCLE=0
while [ $CYCLE -lt $MAX_CYCLES ]; do
    CYCLE=$((CYCLE + 1))

    # Check kill file
    if [ -f "$KILL_FILE" ]; then
        log "Kill file detected. Stopping sprint."
        rm -f "$KILL_FILE"
        exit 0
    fi

    # Check if all tasks are done
    REMAINING=$(grep -c '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
    if [ "$REMAINING" -eq 0 ]; then
        log "All tasks completed! Sprint finished after $CYCLE cycles."
        exit 0
    fi

    NEXT_TASK=$(grep -m1 '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null | sed 's/^- \[ \] //' || echo "unknown")
    log "===== Cycle $CYCLE/$MAX_CYCLES | $REMAINING remaining | Next: $NEXT_TASK ====="

    START_TIME=$(date +%s)

    # Run one cycle using the shared build-cycle.sh script
    bash "$HOLUS_DIR/infra/build-cycle.sh" 2>&1 || true

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    log "Cycle $CYCLE completed in ${DURATION}s ($((DURATION / 60))m $((DURATION % 60))s)"

    # Check kill file after cycle
    if [ -f "$KILL_FILE" ]; then
        log "Kill file detected after cycle. Stopping sprint."
        rm -f "$KILL_FILE"
        exit 0
    fi

    # Cooldown (skip on last cycle)
    if [ $CYCLE -lt $MAX_CYCLES ]; then
        log "Cooling down for ${COOLDOWN}s..."
        sleep $COOLDOWN
    fi
done

log "========================================="
log "Sprint completed after $CYCLE cycles"
COMPLETED=$(grep -c '^\- \[x\]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
REMAINING=$(grep -c '^\- \[ \]' agentic/memory/NEXT.md 2>/dev/null || echo "0")
log "Tasks completed: $COMPLETED"
log "Tasks remaining: $REMAINING"
log "========================================="
