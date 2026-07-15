# Spec 028: Observatory API

**Status:** planned
**Phase:** Phase 2
**Author:** Juan
**Created:** 2026-03-12
**Updated:** 2026-03-12

## Problem

There is no way to observe what the Holus system is doing. Trajectory decisions, agent quality scores, content pipeline state, and per-agent cost data all exist in files — but they are invisible at a glance. A developer running Holus has to grep JSONL files and manually count YAML entries to answer basic questions like "how many content pieces are in review?" or "which agent is failing most?".

The Observatory dashboard (Spec 029) needs a backend to serve this data. Without an API layer, the dashboard either reads files directly from the browser (impossible for server-side paths) or requires a separate file-watching daemon.

## Goals

- All 32 agents returned from `GET /api/v1/agents` with current status and last-run info
- Paginated trajectory entries with filter support (date range, agent_id, content_type)
- SSE endpoint streams new trajectory entries within 5 seconds of file append
- All endpoints respond in < 200ms for datasets up to 10,000 trajectory entries
- CORS configured for localhost:3000 so the Next.js/SvelteKit dev server connects without proxy
- `just dev-api` starts the server in one command
- Zero new databases — all data read from existing files

## Non-Goals

- Authentication — Phase 1 is localhost-only; adding auth before the dashboard exists creates friction with no security benefit
- Write endpoints — the dashboard is read-only; all writes happen through the existing agent system
- Database — trajectory.jsonl and eval_history.jsonl are small enough to read on-demand; introducing a DB here would require a migration path and is premature
- Langfuse API proxying — the Observatory pulls from Langfuse directly in Phase 2; this spec covers file-based data only

## Solution

A FastAPI application at `src/holus/api/` that reads existing files and serves them over HTTP. No new persistence layer — all data already exists in the right format.

```
Observatory Dashboard (SvelteKit/Next.js, port 3000)
          │
          │  REST + SSE (port 8000)
          ▼
  FastAPI app (src/holus/api/)
          │
          ├── agentic/agents/AGENTS.yaml  → /api/v1/agents
          ├── .self-improvement/
          │   ├── memory/trajectory.jsonl → /api/v1/trajectory
          │   └── knowledge/current/*.md  → /api/v1/knowledge
          ├── ~Projects/core/verification/
          │   └── eval_history.jsonl      → /api/v1/evaluations
          └── data/content-queue/*.yaml   → /api/v1/content
```

The SSE endpoint (`/api/v1/trajectory/stream`) uses `sse-starlette`'s `EventSourceResponse` with a file-tail loop that polls `trajectory.jsonl` every 2 seconds and emits new lines.

All endpoints return Pydantic-validated response models. The app mounts at `/api/v1/` with an OpenAPI schema available at `/docs`.

## API Contract

### Agent Registry

```
GET /api/v1/agents

Response (200):
  agents: List[AgentInfo]

GET /api/v1/agents/{agent_id}

Response (200): AgentInfo + full performance history
Response (404): agent_id not found in AGENTS.yaml

GET /api/v1/agents/{agent_id}/metrics

Response (200): AgentMetrics
Response (404): agent_id not found
```

### Trajectory

```
GET /api/v1/trajectory

Query params:
  page: int (default 1)
  page_size: int (default 50, max 200)
  agent_id: str | None — filter by agent
  content_type: str | None — filter by content_type field
  date_from: date | None — inclusive lower bound
  date_to: date | None — inclusive upper bound

Response (200):
  entries: List[TrajectoryEntry]
  total: int
  page: int
  page_size: int
  has_more: bool

GET /api/v1/trajectory/stream

Response: text/event-stream
  event: trajectory_entry
  data: TrajectoryEntry (JSON)

  Emitted within 5s of each new line appended to trajectory.jsonl.
  Connection stays open; client reconnects on drop (EventSource does this automatically).
```

### Content Pipeline

```
GET /api/v1/content

Response (200):
  items: List[ContentItem]
  counts: { draft: int, review: int, published: int, rejected: int }

GET /api/v1/content/calendar

Query params:
  days: int (default 14)

Response (200):
  calendar: List[{ date: date, items: List[ContentItem] }]
```

### Evaluations

```
GET /api/v1/evaluations

Query params:
  agent_id: str | None
  limit: int (default 100, max 500)

Response (200):
  evaluations: List[EvaluationResult]

GET /api/v1/evaluations/summary

Response (200): EvaluationSummary
  avg_score: float
  pass_rate: float        — % of evals above threshold (7.0)
  score_by_agent: dict[str, float]
  trend_7d: List[{ date: date, avg_score: float }]
```

### Knowledge

```
GET /api/v1/knowledge

Response (200):
  files: List[KnowledgeFile]

GET /api/v1/knowledge/{filename}

Response (200): KnowledgeFile with content field populated
Response (404): file not found
```

### System

```
GET /api/v1/health

Response (200): HealthStatus
  kill_switch_active: bool
  trajectory_file_exists: bool
  eval_history_file_exists: bool
  agents_yaml_exists: bool
  content_queue_count: int
  error_rate_1h: float | None    — fraction of trajectory entries with error in last hour

GET /api/v1/metrics

Response (200): KPIMetrics
  total_cycles: int
  success_rate: float
  avg_quality_score: float | None
  total_cost_usd: float | None
  cost_per_approved_asset: float | None
  active_agents_24h: int
  content_published_7d: int
```

## Implementation Notes

### File Layout

```
src/holus/api/
├── __init__.py
├── app.py              — FastAPI app factory, CORS, router registration
├── routes/
│   ├── agents.py
│   ├── trajectory.py   — includes SSE endpoint
│   ├── content.py
│   ├── evaluations.py
│   ├── knowledge.py
│   └── system.py
└── models/
    ├── __init__.py
    └── responses.py    — all Pydantic response models
```

### Pydantic Response Models

```python
class AgentInfo(BaseModel):
    id: str
    name: str
    model: str
    role: str
    last_run: datetime | None
    last_status: str | None     # "success" | "error" | "running" | None
    run_count_7d: int

class AgentMetrics(BaseModel):
    agent_id: str
    avg_quality_score: float | None
    total_runs: int
    success_rate: float
    avg_cost_usd: float | None
    p50_latency_s: float | None
    p95_latency_s: float | None

class TrajectoryEntry(BaseModel):
    timestamp: datetime
    agent_id: str
    content_type: str | None
    action: str
    outcome: str | None         # "success" | "error"
    quality_score: float | None
    cost_usd: float | None
    tokens_used: int | None
    notes: str | None

class ContentItem(BaseModel):
    id: str
    title: str | None
    content_type: str
    status: str                 # "draft" | "review" | "published" | "rejected"
    created_at: datetime | None
    scheduled_for: datetime | None
    agent_id: str | None

class EvaluationResult(BaseModel):
    timestamp: datetime
    agent_id: str
    score: float
    max_score: float
    pass_threshold: float
    passed: bool
    notes: str | None

class EvaluationSummary(BaseModel):
    avg_score: float
    pass_rate: float
    score_by_agent: dict[str, float]
    trend_7d: list[dict]        # [{date, avg_score}]

class KnowledgeFile(BaseModel):
    filename: str
    last_modified: datetime
    size_bytes: int
    content: str | None         # populated only on /knowledge/{filename}

class HealthStatus(BaseModel):
    kill_switch_active: bool
    trajectory_file_exists: bool
    eval_history_file_exists: bool
    agents_yaml_exists: bool
    content_queue_count: int
    error_rate_1h: float | None

class KPIMetrics(BaseModel):
    total_cycles: int
    success_rate: float
    avg_quality_score: float | None
    total_cost_usd: float | None
    cost_per_approved_asset: float | None
    active_agents_24h: int
    content_published_7d: int
```

### SSE Implementation

```python
# routes/trajectory.py
from sse_starlette.sse import EventSourceResponse
import asyncio, json
from pathlib import Path

TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")

async def tail_trajectory():
    last_size = 0
    while True:
        await asyncio.sleep(2)
        if not TRAJECTORY_PATH.exists():
            continue
        current_size = TRAJECTORY_PATH.stat().st_size
        if current_size > last_size:
            with TRAJECTORY_PATH.open() as f:
                f.seek(last_size)
                new_lines = f.read()
            last_size = current_size
            for line in new_lines.splitlines():
                if line.strip():
                    yield {"event": "trajectory_entry", "data": line}

@router.get("/trajectory/stream")
async def stream_trajectory():
    return EventSourceResponse(tail_trajectory())
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

Port 3000 covers Next.js dev server; port 5173 covers SvelteKit (Vite). Both allowed so either frontend framework works during development.

### Data Source Paths

All paths are relative to the Holus repo root and resolved at startup:

| Endpoint group | Source path | Notes |
|---|---|---|
| /agents | `agentic/agents/AGENTS.yaml` | Parse with PyYAML |
| /trajectory | `.self-improvement/memory/trajectory.jsonl` | Read line-by-line; one JSON object per line |
| /evaluations | `~Projects/core/verification/eval_history.jsonl` | Absolute path via env var `EVAL_HISTORY_PATH` |
| /content | `data/content-queue/*.yaml` | Glob all YAML files in directory |
| /knowledge | `agentic/memory/knowledge/current/*.md` | Glob all MD files |
| /health | Multiple (see above) | Check file existence + kill_switch.py |
| /metrics | Computed from trajectory + eval_history | In-memory aggregation on request |

`EVAL_HISTORY_PATH` defaults to `~/.openclaw/workspace/github/~Projects/core/verification/eval_history.jsonl` and is overridable via environment variable.

### Justfile Entry

```makefile
dev-api:
    uv run uvicorn src.holus.api.app:app --reload --port 8000
```

### Dependencies to Add

```toml
# pyproject.toml additions
"fastapi>=0.115.0",
"uvicorn[standard]>=0.32.0",
"sse-starlette>=2.1.0",
"pyyaml>=6.0.2",
```

All are already compatible with the existing Python 3.12 + uv stack.

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| SSE poll interval | 2s | Low enough to feel real-time; high enough to avoid busy-looping |
| Default page_size | 50 | Fits a dashboard view without pagination overhead |
| Max page_size | 200 | Prevents accidental full-file loads on large trajectory files |
| CORS origins | localhost:3000, :5173 | Covers Next.js and SvelteKit dev servers |
| Eval pass threshold | 7.0 | Matches eval_gate.py threshold used in existing scoring system |
| API prefix | /api/v1 | Namespaced for future versioning |

### Dependencies

- Depends on: Spec 001 (core infrastructure — file paths established)
- Depends on: Spec 027 (resilient agent loop — trajectory.jsonl format defined)
- Depended on by: Spec 029 (Observatory dashboard — consumes all endpoints)

## Alternatives Considered

### Alternative A: Direct File Access from the Frontend

The frontend (browser) reads trajectory.jsonl and AGENTS.yaml directly via the file system.

Trade-off: Works in Electron or Tauri desktop apps; fails for browser-based dashboards (browsers cannot access the filesystem).
Rejected because: The target is a browser-served dashboard, not an Electron app.

### Alternative B: WebSocket Instead of SSE

Use a WebSocket connection for real-time trajectory streaming.

Trade-off: WebSocket is bidirectional and has broader server-push support; SSE is simpler, unidirectional, and automatically reconnects via the browser's EventSource.
Rejected because: The dashboard only needs server-push (read-only streaming). SSE is simpler to implement in FastAPI (`sse-starlette`), requires no handshake overhead, and reconnects automatically on drop. WebSocket adds bidirectional complexity with no benefit for a monitoring use case.

### Alternative C: SQLite for Trajectory Data

Load trajectory.jsonl into SQLite at startup for fast filtering and aggregation.

Trade-off: SQLite gives O(1) queries vs O(n) JSONL scans; requires startup loading time and migration logic.
Rejected because: Trajectory files are currently small (< 10,000 entries for months of operation). SQLite adds write synchronization complexity between the agent loop (which appends to JSONL) and the API (which would need to detect new appends and insert them). The JSONL tail pattern is simpler and sufficient at this scale. Revisit at 100K+ entries.

## Edge Cases & Failure Modes

- **trajectory.jsonl does not exist yet:** `/api/v1/trajectory` returns `{entries: [], total: 0}`; `/api/v1/trajectory/stream` waits and emits nothing until the file is created
- **Malformed JSONL line:** Skip the line, log a warning; do not crash the endpoint
- **AGENTS.yaml missing or malformed:** `/api/v1/agents` returns 503 with message `agents registry unavailable`
- **eval_history.jsonl not found at configured path:** `/api/v1/evaluations` returns `{evaluations: []}` with a warning header `X-Data-Source: unavailable`
- **content-queue directory empty:** `/api/v1/content` returns `{items: [], counts: {draft:0, review:0, published:0, rejected:0}}`
- **SSE client disconnects:** FastAPI/starlette detects disconnect; the generator exits cleanly; no resource leak
- **Two SSE clients simultaneously:** Each gets its own generator coroutine reading from the same file — safe for concurrent reads (append-only file)
- **Large trajectory file (> 100K lines):** Pagination handles reads correctly; SSE tail only reads new bytes (not full file replay on reconnect)

## Observability

The API itself is lightweight enough that no additional monitoring is needed in Phase 1. Key log events:

- Startup: log resolved paths for all data sources; warn if any are missing
- Every SSE connection opened/closed: log client IP + connection duration
- Any JSONL parse error: log line number and raw content (truncated to 200 chars)
- Health endpoint: log any file missing at WARN level

## Open Questions

- [ ] Should `/api/v1/trajectory/stream` replay the last N entries on connect, or start from "now"? — @Juan (affects reconnect UX in the dashboard)
- [ ] Is `EVAL_HISTORY_PATH` always at the workspace level, or will it move into the Holus repo eventually? — @Juan (affects default path logic)

## Acceptance Criteria

- [ ] FastAPI app starts with `just dev-api` and serves at `http://localhost:8000`
- [ ] `GET /api/v1/agents` returns all agents defined in `agentic/agents/AGENTS.yaml`
- [ ] `GET /api/v1/agents/{agent_id}` returns 404 for an unknown agent_id
- [ ] `GET /api/v1/trajectory` returns paginated results with correct `total` and `has_more` fields
- [ ] `GET /api/v1/trajectory?agent_id=marketing-strategist` filters correctly
- [ ] `GET /api/v1/trajectory/stream` delivers an SSE event within 5 seconds of a new line being appended to trajectory.jsonl
- [ ] `GET /api/v1/health` returns correct `kill_switch_active` state
- [ ] `GET /api/v1/evaluations/summary` returns `pass_rate` as a float between 0 and 1
- [ ] All endpoints return Pydantic-validated response models (validated by FastAPI schema at `/docs`)
- [ ] CORS allows requests from `http://localhost:3000` and `http://localhost:5173`
- [ ] Missing or empty data files return empty collections (not 500 errors)
- [ ] `uv run pytest -q` passes with at least route-level smoke tests for each endpoint group
