# Dashboard & API

**Spec ID:** 008
**Status:** Draft
**Role:** Backend Developer
**Priority:** High (MVP)
**Created:** 2026-02-08

## Problem / Goal

Holus agents run autonomously in the background, but there is no way to monitor their status, view run history, trigger manual runs, or inspect logs without reading terminal output. The orchestrator hub spec (001) lists a FastAPI dashboard at `:8080` as a requirement, but it is not yet implemented.

The user needs a lightweight, local-first control panel to see at a glance whether agents are healthy, what they've done recently, and to trigger manual runs or view configuration.

## Solution Overview

Implement a FastAPI-based REST API (`dashboard/app.py`) with server-rendered HTML pages using Jinja2 + HTMX for a zero-JS-build dashboard. The API serves both human-browsable pages and JSON endpoints for programmatic access.

## User Stories

- **US-001:** As a user, I want to see the status of all my agents on a single page so I know what's running and what's not.
- **US-002:** As a user, I want to see the last N runs for each agent with timestamps and results so I can track performance.
- **US-003:** As a user, I want to trigger a manual agent run from the dashboard so I don't need the CLI.
- **US-004:** As a user, I want a health check endpoint so I can monitor Holus from external tools.
- **US-005:** As a user, I want to view agent configuration (non-secret fields) so I can verify settings.

## Numbered Specifications

### SPEC-001: Health Check Endpoint
- `GET /api/health` returns `{"status": "ok", "uptime_seconds": <int>, "agent_count": <int>}`.
- Response code is 200 when healthy, 503 when scheduler is not running.

**Acceptance Criteria:**
- [ ] Returns 200 with JSON body when orchestrator is running
- [ ] Returns 503 when scheduler has stopped
- [ ] Includes `uptime_seconds` as integer
- [ ] Includes `agent_count` as integer

### SPEC-002: Agent List Endpoint
- `GET /api/agents` returns a JSON array of all registered agents with: `name`, `description`, `schedule`, `enabled`, `run_count`, `last_run` (ISO timestamp or null), `status` ("idle" | "running" | "error").

**Acceptance Criteria:**
- [ ] Returns JSON array of agent objects
- [ ] Each object contains all specified fields
- [ ] `last_run` is null if agent has never run, ISO string otherwise
- [ ] `status` reflects current execution state

### SPEC-003: Agent Detail Endpoint
- `GET /api/agents/{agent_name}` returns full detail for one agent including config (with secrets redacted), recent run results (last 10), and current status.
- Returns 404 with `{"error": "Agent not found"}` for unknown agent names.

**Acceptance Criteria:**
- [ ] Returns agent detail with config, recent runs, and status
- [ ] Secrets (api_key, token, password, secret) are replaced with `"***REDACTED***"`
- [ ] Returns 404 JSON for nonexistent agent names
- [ ] Recent runs are ordered newest-first, limited to 10

### SPEC-004: Manual Run Endpoint
- `POST /api/agents/{agent_name}/run` triggers an immediate asynchronous run of the specified agent.
- Returns 202 with `{"status": "started", "agent": "<name>"}` immediately.
- Returns 404 if agent not found.
- Returns 409 if agent is already running.

**Acceptance Criteria:**
- [ ] Returns 202 and launches agent run asynchronously
- [ ] Returns 404 for nonexistent agent
- [ ] Returns 409 if agent is currently mid-run
- [ ] Does not block the HTTP response on agent completion

### SPEC-005: Dashboard HTML Page
- `GET /` renders an HTML page showing all agents in a card grid.
- Each card shows: agent name, status badge (green=idle, yellow=running, red=error), schedule, run count, last run time.
- Each card has a "Run Now" button that triggers SPEC-004 via HTMX.
- Page auto-refreshes agent status every 10 seconds via HTMX polling.

**Acceptance Criteria:**
- [ ] Renders valid HTML with Jinja2
- [ ] Shows one card per registered agent
- [ ] Status badge color matches agent state
- [ ] "Run Now" button triggers POST and updates card without full page reload
- [ ] Auto-polls `/api/agents` every 10 seconds

### SPEC-006: Run History Endpoint
- `GET /api/agents/{agent_name}/runs?limit=20` returns the last N run results from memory.
- Each run entry includes: `run_number`, `timestamp`, `status` (completed | error), `result_summary` (first 200 chars of result), `duration_seconds`.

**Acceptance Criteria:**
- [ ] Returns JSON array of run entries, newest first
- [ ] Respects `limit` query param (default 20, max 100)
- [ ] Each entry has all specified fields
- [ ] Returns empty array if no runs exist

### SPEC-007: Agent Config Endpoint
- `GET /api/agents/{agent_name}/config` returns the agent's config with secrets redacted.
- Secrets are any keys containing: `key`, `token`, `secret`, `password`, `credential`.

**Acceptance Criteria:**
- [ ] Returns agent config as JSON
- [ ] All secret-containing keys are redacted
- [ ] Returns 404 for unknown agents
- [ ] Nested secret keys are also redacted

### SPEC-008: Dashboard Integration with Orchestrator
- The dashboard starts alongside the orchestrator (same process).
- Uvicorn runs in a background thread so it doesn't block the async scheduler.
- Dashboard is disabled if `dashboard.enabled` is false in config.
- Binds to `dashboard.host` and `dashboard.port` from config.

**Acceptance Criteria:**
- [ ] Dashboard starts automatically with `python -m holus.main`
- [ ] Uvicorn runs without blocking the scheduler
- [ ] Dashboard can be disabled via config
- [ ] Host and port are configurable

## Edge Cases

- **EDGE-001:** Agent name contains special characters → validate and reject with 400.
- **EDGE-002:** Manual run triggered while agent is mid-run → return 409 Conflict.
- **EDGE-003:** Orchestrator has no agents registered → dashboard shows empty state message.
- **EDGE-004:** Config file has no `dashboard` section → use defaults (host=0.0.0.0, port=8080, enabled=true).
- **EDGE-005:** Memory store is empty for an agent → run history returns empty array.
- **EDGE-006:** Agent run fails with exception → status shows "error", last run still recorded.

## State Definitions

| State | Condition | Display |
|-------|-----------|---------|
| **Loading** | Dashboard fetching data | Skeleton cards with pulsing animation |
| **Empty** | No agents registered | "No agents registered. Check your config." |
| **Idle** | Agent not running | Green badge, "Run Now" enabled |
| **Running** | Agent mid-execution | Yellow badge, "Run Now" disabled, spinner |
| **Error** | Last run failed | Red badge, error message shown |
| **Success** | Data loaded | Agent cards with full info |

## Security Considerations

- Dashboard binds to `0.0.0.0` by default — appropriate for local network (Mac Mini).
- No authentication for MVP (local-only deployment).
- All secret config values are redacted in API responses.
- Agent name parameter is validated (alphanumeric + underscore only) to prevent injection.
- No file system access exposed through API.

## Data / API Changes

No new database tables. Run history is stored in the existing ChromaDB agent memory collections. The dashboard reads from the in-memory orchestrator state and ChromaDB.

### API Summary

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/health` | Health status |
| GET | `/api/agents` | Agent list |
| GET | `/api/agents/{name}` | Agent detail |
| POST | `/api/agents/{name}/run` | Trigger run |
| GET | `/api/agents/{name}/runs` | Run history |
| GET | `/api/agents/{name}/config` | Agent config |
| GET | `/` | Dashboard HTML |

## Out of Scope

- Authentication / authorization (future: add API key or basic auth)
- WebSocket real-time updates (HTMX polling is sufficient for MVP)
- Log streaming (future enhancement)
- Agent configuration editing via API
- Mobile-responsive design (desktop is primary for local monitoring)

## Open Questions

None — all pending questions resolved by relying on existing config patterns and MVP scope.

## Dependencies

- FastAPI (already in requirements.txt)
- Uvicorn (already in requirements.txt)
- Jinja2 (already in requirements.txt)
- HTMX (loaded from CDN, no build step)

## Implementation Notes

- Place API logic in `dashboard/app.py`
- Place templates in `dashboard/templates/`
- The FastAPI app receives a reference to the orchestrator instance
- Use `threading.Thread` with `uvicorn.run()` to avoid blocking the async loop
- Keep templates minimal — single-file Jinja2 with HTMX attributes
