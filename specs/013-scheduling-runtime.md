# Spec 013: Scheduling & Runtime

**Status:** partial
**Phase:** Phase 1
**Author:** Camilo Martinez
**Created:** 2026-02-26
**Updated:** 2026-02-26

## Problem

Holus currently requires manual invocation to run the marketing agent and self-improvement cycles. Without automated scheduling, content creation stops whenever the founder is away, health issues go undetected until someone manually checks, and log files accumulate without rotation. The system needs to operate autonomously so it works while the founder sleeps.

## Goals

- Marketing agent runs automatically every 30 minutes without manual intervention
- Self-improvement cycle runs weekly on a fixed schedule (Sunday 7am)
- Health checks run every 5 minutes and detect degraded services
- System starts and stops with a single command (`just schedule` / `just unschedule`)
- Log rotation prevents disk space exhaustion (no log file exceeds 100MB)
- Run locks prevent overlapping agent instances
- CLI entrypoint supports all runtime operations (`run`, `status`, `kill`, `unkill`, `health`)

## Non-Goals

- Remote monitoring (Datadog, PagerDuty, etc.) -- Phase 2+ when we have production infrastructure
- Multi-machine deployment -- Holus runs on a single Mac Mini for now
- Container orchestration -- Docker is for services only, agents run natively on macOS
- Telegram bot for notifications -- separate future spec
- Privilege escalation -- launchd runs as the local user, no root access needed

## Solution

The runtime infrastructure uses macOS launchd for scheduling, flock-based run locks for overlap prevention, and a unified CLI entrypoint (`python -m holus`) for all operations.

Three launchd plists schedule the system:
1. **Marketing agent** (every 30 min) -- runs one observe-reason-act cycle
2. **Self-improvement** (weekly Sunday 7am) -- runs `just improve`
3. **Health check** (every 5 min) -- verifies kill switch, trajectory, knowledge, content queue, and logs

The CLI provides manual control: run agents, check status, toggle kill switches, and run health checks. All operations check the kill switch before executing.

Logs go to `logs/` (gitignored) with a rotation mechanism that archives files over 10MB and deletes archives older than 7 days.

Security: launchd runs as the local user (no privilege escalation). Log files may contain agent reasoning but never secrets. The kill switch is accessible without authentication (intentional for emergency access). Health checks do not expose secrets.

## Implementation Notes

### SPEC-001: CLI Entrypoint

| Field | Value |
|-------|-------|
| Description | `python -m holus` CLI that starts agents, checks status, and manages the system |
| Trigger | Manual or launchd |
| Input | CLI arguments (agent name, command) |
| Output | Agent execution or status report |
| Validation | Agent name must be known. Kill switch checked before starting. |
| Auth Required | No |

```python
# src/holus/__main__.py

from __future__ import annotations

import argparse
import asyncio
import sys

from holus.core.run_lock import acquire_run_lock


def main() -> None:
    parser = argparse.ArgumentParser(prog="holus", description="Holus AI Marketing Agent")
    subparsers = parser.add_subparsers(dest="command")

    # Run an agent
    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument("agent", choices=["marketing", "manager", "all"])
    run_parser.add_argument("--once", action="store_true", help="Run one cycle and exit")

    # Check status
    subparsers.add_parser("status", help="Show system status")

    # Kill switch
    kill_parser = subparsers.add_parser("kill", help="Activate kill switch")
    kill_parser.add_argument("--scope", required=True)
    kill_parser.add_argument("--reason", required=True)

    # Unkill
    unkill_parser = subparsers.add_parser("unkill", help="Deactivate kill switch")
    unkill_parser.add_argument("--scope", required=True)

    # Health check
    subparsers.add_parser("health", help="Run health check")

    args = parser.parse_args()

    if args.command == "run":
        with acquire_run_lock(f"holus-{args.agent}"):
            asyncio.run(run_agent(args.agent, once=args.once))
    elif args.command == "status":
        show_status()
    elif args.command == "kill":
        activate_kill(args.scope, args.reason)
    elif args.command == "unkill":
        deactivate_kill(args.scope)
    elif args.command == "health":
        run_health_check()
    else:
        parser.print_help()
        sys.exit(1)


async def run_agent(agent_name: str, once: bool = False) -> None:
    if agent_name == "marketing":
        from holus.agents.marketing.agent import MarketingAgent
        agent = MarketingAgent()
        await agent.run()
    elif agent_name == "manager":
        # Run self-improvement cycle
        pass
    await agent.close()


if __name__ == "__main__":
    main()
```

### SPEC-002: launchd Scheduler Plists

| Field | Value |
|-------|-------|
| Description | macOS launchd plists for marketing agent (every 30 min), self-improvement (weekly), and health check (every 5 min) |
| Trigger | System timer |
| Input | None |
| Output | Agent runs, logs written |
| Validation | launchd loaded and running |
| Auth Required | No |

```xml
<!-- infra/launchd/com.holus.marketing.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.holus.marketing</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd /Users/mini/.openclaw/workspace/github/holus && .venv/bin/python -m holus run marketing --once >> logs/marketing.log 2>&1</string>
    </array>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/marketing.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/marketing.stderr.log</string>
</dict>
</plist>
```

```xml
<!-- infra/launchd/com.holus.improve.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.holus.improve</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd /Users/mini/.openclaw/workspace/github/holus && just improve >> logs/improve.log 2>&1</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>7</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/improve.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/improve.stderr.log</string>
</dict>
</plist>
```

```xml
<!-- infra/launchd/com.holus.health.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.holus.health</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd /Users/mini/.openclaw/workspace/github/holus && .venv/bin/python -m holus health</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>StandardOutPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/health.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mini/.openclaw/workspace/github/holus/logs/health.stderr.log</string>
</dict>
</plist>
```

Justfile commands:

```just
# Schedule all Holus agents
schedule:
    mkdir -p logs
    cp infra/launchd/com.holus.*.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/com.holus.marketing.plist
    launchctl load ~/Library/LaunchAgents/com.holus.improve.plist
    launchctl load ~/Library/LaunchAgents/com.holus.health.plist
    @echo "All Holus agents scheduled."

# Unschedule all
unschedule:
    -launchctl unload ~/Library/LaunchAgents/com.holus.marketing.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.improve.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.health.plist 2>/dev/null
    @echo "All Holus agents unscheduled."

# Show schedule status
schedule-status:
    @echo "=== Scheduled Holus Agents ==="
    @launchctl list | grep holus || echo "No agents scheduled"
    @echo "\n=== Recent Logs ==="
    @tail -5 logs/marketing.log 2>/dev/null || echo "No marketing logs"
    @tail -5 logs/health.log 2>/dev/null || echo "No health logs"

# Run marketing agent once
run-marketing:
    python -m holus run marketing --once
```

### SPEC-003: Health Check

| Field | Value |
|-------|-------|
| Description | Quick health check that verifies core services and agent status |
| Trigger | Every 5 minutes via launchd, or manual `python -m holus health` |
| Input | None |
| Output | Health status to stdout (and optionally Telegram) |
| Validation | All checks complete within 30 seconds |
| Auth Required | No |

```python
# src/holus/core/health.py

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger()


class HealthCheck:
    def run(self) -> dict:
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "overall": "healthy",
        }

        # Check kill switch
        results["checks"]["kill_switch"] = self.check_kill_switch()

        # Check trajectory file writable
        results["checks"]["trajectory"] = self.check_trajectory()

        # Check knowledge base readable
        results["checks"]["knowledge"] = self.check_knowledge()

        # Check content queue
        results["checks"]["content_queue"] = self.check_content_queue()

        # Check logs directory
        results["checks"]["logs"] = self.check_logs()

        # Overall status
        if any(
            c.get("status") == "unhealthy"
            for c in results["checks"].values()
        ):
            results["overall"] = "unhealthy"

        return results

    def check_kill_switch(self) -> dict:
        try:
            import redis
            import os
            r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
            r.ping()
            global_kill = r.exists("holus:kill:global")
            return {
                "status": "healthy",
                "redis": "connected",
                "global_kill_active": bool(global_kill),
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e), "note": "Redis not required for Phase 1"}

    def check_trajectory(self) -> dict:
        path = Path(".self-improvement/memory/trajectory.jsonl")
        return {
            "status": "healthy",
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }

    def check_knowledge(self) -> dict:
        knowledge_dir = Path("agentic/memory/knowledge/current")
        files = list(knowledge_dir.glob("*.md")) if knowledge_dir.exists() else []
        return {
            "status": "healthy" if files else "degraded",
            "files_count": len(files),
            "files": [f.name for f in files],
        }

    def check_content_queue(self) -> dict:
        queue_dir = Path("data/content-queue")
        if not queue_dir.exists():
            return {"status": "healthy", "pending": 0}
        pending = list(queue_dir.glob("*.yaml"))
        return {"status": "healthy", "pending": len(pending)}

    def check_logs(self) -> dict:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return {"status": "degraded", "note": "logs/ directory missing"}
        return {"status": "healthy", "directory": str(logs_dir)}
```

### SPEC-004: Log Management

| Field | Value |
|-------|-------|
| Description | Log rotation and cleanup to prevent disk usage issues |
| Trigger | Daily or when log files exceed size threshold |
| Input | Log files in `logs/` |
| Output | Rotated/compressed log files |
| Validation | No log file exceeds 100MB |
| Auth Required | No |

```just
# Rotate logs (keep last 7 days)
rotate-logs:
    @mkdir -p logs/archive
    @for f in logs/*.log; do \
        if [ -f "$f" ] && [ $(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null) -gt 10485760 ]; then \
            mv "$f" "logs/archive/$(basename $f).$(date +%Y%m%d)"; \
            touch "$f"; \
        fi \
    done
    @find logs/archive -mtime +7 -delete 2>/dev/null || true
    @echo "Logs rotated."
```

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/__main__.py` | New | CLI entrypoint |
| `src/holus/core/health.py` | New | Health check system |
| `src/holus/core/run_lock.py` | New | Run lock for overlap prevention |
| `infra/launchd/com.holus.marketing.plist` | New | Marketing agent scheduler |
| `infra/launchd/com.holus.improve.plist` | New | Self-improvement scheduler |
| `infra/launchd/com.holus.health.plist` | New | Health check scheduler |
| `justfile` | Modified | Add schedule, unschedule, run-marketing, health commands |
| `logs/` | New (gitignored) | Log output directory |
| `tests/unit/core/test_health.py` | New | Health check tests |

### Dependencies

- Depends on: [Spec 009](./009-autonomous-build-system.md) — also uses launchd and run locks
- Depends on: [Spec 010](./010-marketing-agent.md) — the primary agent being scheduled
- Depends on: [Spec 001](./001-core-infrastructure.md) — Docker services that support the runtime

## Edge Cases & Failure Modes

**EDGE-001: launchd fails to load plist**
- Scenario: plist has invalid syntax or paths don't exist
- Expected behavior: `launchctl load` reports error with description
- Recovery: Fix plist syntax, ensure paths exist, reload

**EDGE-002: Agent crashes during scheduled run**
- Scenario: Marketing agent crashes mid-cycle
- Expected behavior: Run lock is auto-released (flock guarantee). Error logged. Next scheduled run starts fresh.
- Recovery: Automatic. Health check detects and reports.

**EDGE-003: Disk full**
- Scenario: Log files fill up the disk
- Expected behavior: Health check detects and reports. Log rotation runs.
- Recovery: `just rotate-logs` frees space. Health check reports "unhealthy" until resolved.

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| CLI startup | < 2s | Time to first output |
| Health check | < 10s | Time to complete all checks |
| launchd load/unload | < 1s | launchctl response time |

## Acceptance Criteria

- [ ] `python -m holus run marketing --once` runs one marketing cycle
- [ ] `python -m holus status` shows agent status and kill switch state
- [ ] `python -m holus kill --scope marketing-agent --reason "testing"` activates kill switch
- [ ] `python -m holus unkill --scope marketing-agent` deactivates kill switch
- [ ] `python -m holus health` runs all checks and reports status
- [ ] Run lock prevents overlapping instances
- [ ] `just schedule` installs and loads all launchd plists
- [ ] `just unschedule` removes all launchd agents
- [ ] `just schedule-status` shows running agents and recent logs
- [ ] Marketing agent runs every 30 minutes
- [ ] Self-improvement runs weekly on Sunday at 7am
- [ ] Health check runs every 5 minutes
- [ ] Logs written to `logs/` directory
- [ ] Health check completes within 30 seconds
- [ ] Redis failure is "degraded" not "unhealthy" (not required for Phase 1)
- [ ] Health check output is JSON for programmatic consumption
- [ ] Health check itself is logged
- [ ] `just rotate-logs` rotates logs larger than 10MB
- [ ] Old archives (>7 days) are automatically deleted
- [ ] Log rotation doesn't interrupt running agents
- [ ] `logs/` directory is gitignored
