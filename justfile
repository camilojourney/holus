# Holus — unified task runner
# Run `just` or `just --list` to see all commands.

default:
    @just --list

# -- Setup -------------------------------------------------------------------

install:
    uv sync --all-extras

# -- Run ---------------------------------------------------------------------

run:
    uv run python -m holus

run-agent agent:
    uv run python -m holus agent start {{agent}}

run-all:
    uv run python -m holus agent start --all

# -- Test --------------------------------------------------------------------

test:
    uv run pytest tests/ -x -v

test-unit:
    uv run pytest tests/unit/ -x -v

test-integration:
    uv run pytest tests/integration/ -x -v

test-cov:
    uv run pytest tests/ --cov=src/holus --cov-report=term-missing --cov-report=html

# -- Code Quality ------------------------------------------------------------

lint:
    uv run ruff check src/ tests/
    uv run mypy src/

format:
    uv run ruff format src/ tests/
    uv run ruff check src/ tests/ --fix

format-check:
    uv run ruff format src/ tests/ --check

check: lint format-check test

# -- Docker / Infrastructure -------------------------------------------------

up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

reset:
    docker compose down -v

# -- Utilities ---------------------------------------------------------------

clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

# -- Preflight ---------------------------------------------------------------

# Validate environment before running (API keys, config, knowledge files)
preflight:
    uv run python -m holus.preflight

# -- Marketing Agent ---------------------------------------------------------

# Generate ONE content cycle (no publishing). Requires ANTHROPIC_API_KEY.
generate:
    uv run python -m holus.generate

run-marketing:
    uv run python -m holus run marketing --once

# Review pending social media content
review-content:
    uv run python -m holus.agents.marketing.review

# Approve a content piece for publishing
approve-content piece_id:
    uv run python -m holus.agents.marketing.review --approve {{piece_id}}

# Reject a content piece
reject-content piece_id reason="":
    uv run python -m holus.agents.marketing.review --reject {{piece_id}} --reason "{{reason}}"

# Publish approved content (use --dry-run to preview without posting)
publish *args:
    uv run python -m holus.agents.marketing.publish_approved {{args}}

# Publish all approved content to social media (alias, no dry-run)
publish-approved:
    uv run python -m holus.agents.marketing.publish_approved

# Show weekly content calendar (pipeline status overview)
calendar *args:
    uv run python -m holus.agents.marketing.calendar_view {{args}}

# Review pending videos
review-videos:
    uv run python -m holus.agents.marketing.review_videos

# Approve a video for Genpeli delivery
approve-video piece_id:
    uv run python -m holus.agents.marketing.review_videos --approve {{piece_id}}

# Reject a video
reject-video piece_id reason="":
    uv run python -m holus.agents.marketing.review_videos --reject {{piece_id}} --reason "{{reason}}"

# -- Autonomous Build Sprint (cron-based) -----------------------------------

# Run ONE build cycle (picks next task, implements, logs, commits)
build-cycle:
    bash infra/build-cycle.sh

# Start the 80-cycle sprint via launchd cron (every 20 min)
sprint-start:
    mkdir -p logs
    @echo '{"cycle": 0, "max_cycles": 80, "status": "running", "started_at": null, "interval_minutes": 20}' > .self-improvement/sprint-state.json
    cp infra/launchd/com.holus.builder.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/com.holus.builder.plist
    @echo "Sprint started! Builder will run every 20 min for 80 cycles (~27 hours)."
    @echo "Monitor: just sprint-status"
    @echo "Stop:    just sprint-stop"

# Stop the sprint (graceful — finishes current cycle first)
sprint-stop:
    touch /tmp/holus-stop
    -launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist 2>/dev/null
    @echo "Sprint stopped. Kill file created + cron unloaded."
    @echo "To resume: just sprint-resume"

# Resume a stopped sprint (keeps cycle count)
sprint-resume:
    rm -f /tmp/holus-stop
    cp infra/launchd/com.holus.builder.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/com.holus.builder.plist
    @echo "Sprint resumed from where it left off."

# Reset sprint (start fresh from cycle 0)
sprint-reset:
    -launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist 2>/dev/null
    rm -f /tmp/holus-stop
    @echo '{"cycle": 0, "max_cycles": 80, "status": "ready", "started_at": null, "interval_minutes": 20}' > .self-improvement/sprint-state.json
    @echo "Sprint reset to cycle 0."

# Full sprint status dashboard
sprint-status:
    @echo "=== Sprint State ==="
    @cat .self-improvement/sprint-state.json 2>/dev/null || echo "No sprint state"
    @echo ""
    @echo "=== Tasks ==="
    @printf "Remaining: "; grep -c '^\- \[ \]' .self-improvement/NEXT.md 2>/dev/null || echo "0"
    @printf "Completed: "; grep -c '^\- \[x\]' .self-improvement/NEXT.md 2>/dev/null || echo "0"
    @echo ""
    @echo "=== Cron Status ==="
    @launchctl list 2>/dev/null | grep holus.builder || echo "Builder cron not loaded"
    @echo ""
    @echo "=== Recent Cycle Logs ==="
    @ls -lt logs/cycle-*.log 2>/dev/null | head -5 || echo "No cycle logs yet"
    @echo ""
    @echo "=== Recent Reports ==="
    @ls -lt .self-improvement/reports/builder/*.md 2>/dev/null | head -5 || echo "No reports yet"
    @echo ""
    @echo "=== Sprint Log (last 15 lines) ==="
    @tail -15 logs/sprint.log 2>/dev/null || echo "No sprint log yet"

# Run the old loop-style sprint (alternative to cron)
sprint-loop:
    bash infra/build-sprint.sh

# -- Scheduling (launchd) — marketing + health crons -----------------------

# Validate all launchd plist files (syntax + paths)
validate-plists:
    @echo "=== Plist Syntax ==="
    @plutil -lint infra/launchd/com.holus.marketing.plist
    @plutil -lint infra/launchd/com.holus.health.plist
    @plutil -lint infra/launchd/com.holus.improve.plist
    @plutil -lint infra/launchd/com.holus.builder.plist
    @echo ""
    @echo "=== Path Checks ==="
    @test -d /Users/mini/.openclaw/workspace/github/holus && echo "PASS: working directory exists" || echo "FAIL: working directory missing"
    @test -x /opt/homebrew/bin/uv && echo "PASS: uv found at /opt/homebrew/bin/uv" || echo "FAIL: uv not found"
    @test -x /opt/homebrew/bin/just && echo "PASS: just found at /opt/homebrew/bin/just" || echo "FAIL: just not found"
    @test -d logs && echo "PASS: logs/ directory exists" || echo "WARN: logs/ missing — run mkdir -p logs"
    @echo ""
    @echo "All plist validation complete."

# Test scheduling by running health check once (safe, no API keys needed)
schedule-test:
    @mkdir -p logs
    @echo "Running health check to verify plist command works..."
    @cd /Users/mini/.openclaw/workspace/github/holus && /opt/homebrew/bin/uv run python -m holus health
    @echo ""
    @echo "Health check succeeded. Plist command is valid."

schedule:
    mkdir -p logs
    cp infra/launchd/com.holus.marketing.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    cp infra/launchd/com.holus.improve.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    cp infra/launchd/com.holus.health.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.marketing.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.improve.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.health.plist 2>/dev/null || true
    @echo "All Holus agents scheduled."

unschedule:
    -launchctl unload ~/Library/LaunchAgents/com.holus.marketing.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.improve.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.health.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.builder.plist 2>/dev/null
    @echo "All Holus agents unscheduled."

schedule-status:
    @echo "=== Scheduled Holus Agents ==="
    @launchctl list 2>/dev/null | grep holus || echo "No agents scheduled"
    @echo ""
    @echo "=== Recent Logs ==="
    @tail -5 logs/marketing.log 2>/dev/null || echo "No marketing logs"
    @tail -5 logs/builder.stdout.log 2>/dev/null || echo "No builder logs"
    @tail -5 logs/health.log 2>/dev/null || echo "No health logs"

# -- Observatory API ---------------------------------------------------------

# Start the Observatory API server (reads agent/trajectory/content files, serves at :8000)
dev-api:
    uv run uvicorn holus.api.app:app --reload --port 8000

# Start Observatory API (port 8001) + frontend (port 3000) for local dev
dev-observatory:
    (cd observatory && uv run python -m observatory.api.main &) && \
    cd observatory/frontend && pnpm dev

# Start only the Observatory frontend (API must be running separately at :8001)
dev-observatory-frontend:
    cd observatory/frontend && pnpm dev

# Build Observatory frontend for production
build-observatory:
    cd observatory/frontend && pnpm build

# -- Health ------------------------------------------------------------------

health:
    uv run python -m holus health

# -- Autonomous Content Engine -----------------------------------------------

# Run ONE autonomous content cycle: generate → judge → auto-publish
content-cycle *args:
    uv run python -m holus.agents.marketing.orchestrator content {{args}}

# Collect analytics for published content (run daily)
collect-analytics:
    uv run python -m holus.agents.marketing.orchestrator analytics

# Run improvement cycle: learn → evolve prompts → evaluate A/B tests
improve-cycle:
    uv run python -m holus.agents.marketing.orchestrator improve

# Auto-publish pending content based on judge scores
auto-publish:
    uv run python -c "import asyncio; from holus.agents.marketing.auto_publish import process_queue; print(asyncio.run(process_queue()))"

# Auto-publish dry run (preview without actually posting)
auto-publish-dry:
    uv run python -c "import asyncio; from holus.agents.marketing.auto_publish import process_queue; print(asyncio.run(process_queue(dry_run=True)))"

# Show open capability + knowledge gaps
gaps:
    @echo "=== Capability Gaps (need /code to fix) ==="
    @ls -1 .self-improvement/capability-requests/*.md 2>/dev/null | grep -v README || echo "  None"
    @echo ""
    @echo "=== Knowledge Gaps (expert agent auto-resolves) ==="
    @ls -1 .self-improvement/knowledge/requests/*.md 2>/dev/null | grep -v README || echo "  None"

# Show Thompson Sampling arm performance
arms:
    @cat .self-improvement/bandit_arms.json 2>/dev/null | python3 -m json.tool || echo "No arms data yet"

# Show self-improvement status dashboard
improvement-status:
    @echo "=== Trajectory ==="
    @wc -l < .self-improvement/memory/trajectory.jsonl 2>/dev/null || echo "0 entries"
    @echo ""
    @echo "=== Latest Judge Scores ==="
    @tail -5 .self-improvement/memory/trajectory.jsonl 2>/dev/null | python3 -c "import sys,json; [print(f'  {json.loads(l).get(\"agent_id\",\"?\")}: {json.loads(l).get(\"judge_score\",\"?\")}'[:60]) for l in sys.stdin if l.strip()]" 2>/dev/null || echo "  No entries"
    @echo ""
    @echo "=== Activation Gates ==="
    @printf "  Trajectory entries: "; wc -l < .self-improvement/memory/trajectory.jsonl 2>/dev/null || echo "0"
    @printf "  TS active (need 30/arm): "; cat .self-improvement/bandit_arms.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_observations',0))" 2>/dev/null || echo "0"
    @echo ""
    @echo "=== Open Gaps ==="
    @printf "  Capability: "; ls .self-improvement/capability-requests/*.md 2>/dev/null | grep -c -v README || echo "0"
    @printf "  Knowledge:  "; ls .self-improvement/knowledge/requests/*.md 2>/dev/null | grep -c -v README || echo "0"

# Run load test (100 simulated entries)
load-test:
    uv run python scripts/load_test.py

# Schedule ALL autonomous crons (content + analytics + improvement)
schedule-autonomous:
    mkdir -p logs
    cp infra/launchd/com.holus.marketing.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    cp infra/launchd/com.holus.analytics.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    cp infra/launchd/com.holus.improve.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    cp infra/launchd/com.holus.health.plist ~/Library/LaunchAgents/ 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.marketing.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.analytics.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.improve.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.holus.health.plist 2>/dev/null || true
    @echo "All autonomous crons scheduled:"
    @echo "  Content: every 6h"
    @echo "  Analytics: daily 6am"
    @echo "  Improvement: weekly Sunday"
    @echo "  Health: every 5 min"

# Unschedule all autonomous crons
unschedule-autonomous:
    -launchctl unload ~/Library/LaunchAgents/com.holus.marketing.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.analytics.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.improve.plist 2>/dev/null
    -launchctl unload ~/Library/LaunchAgents/com.holus.health.plist 2>/dev/null
    @echo "All autonomous crons unscheduled."

# -- Self-Improvement --------------------------------------------------------

# Run the weekly learning loop (pattern extraction from trajectory + analytics)
learn:
    uv run python -m holus.self_improvement.learning_loop

# Run the full manager self-improvement cycle (interactive)
improve:
    claude --agent .claude/agents/manager.md

audit:
    claude --agent .claude/agents/security-sentinel.md

# -- Agent Registry ----------------------------------------------------------

# List all agents with their status (from AGENTS.yaml)
agents:
    uv run python scripts/list_agents.py

# Run domain-expert judge on recent trajectory entries (last 7 days)
evaluate:
    uv run python -m holus.cli evaluate --days 7

# Show per-agent cost breakdown from trajectory.jsonl
costs:
    uv run python -m holus.cli costs --group-by agent

# -- Logs --------------------------------------------------------------------

rotate-logs:
    @mkdir -p logs/archive
    @find logs -maxdepth 1 -name "*.log" -size +10M -exec sh -c 'mv {} logs/archive/$$(basename {}).$(date +%Y%m%d)' \;
    @find logs/archive -mtime +7 -delete 2>/dev/null || true
    @echo "Logs rotated."
