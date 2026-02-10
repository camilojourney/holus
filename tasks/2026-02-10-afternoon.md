# Task Specs — 2026-02-10 Afternoon Cycle

## Task 1: MCP Wrapper for Social Media Auto

**Status:** In Progress  
**Repo:** `~/.openclaw/workspace/github/social-media-automatization`  
**Create:** `mcp_server/` directory  
**Estimated:** 4h  

### Context

The social-media-automatization repo has a full pipeline:
- `src/content/text_enhancer.py` — AI text enhancement (Claude/GPT), returns `EnhancedText`
- `src/content/translator.py` — DeepL translation (EN↔ES), returns `TranslationResult`
- `src/content/scheduler.py` — Scheduling with `ScheduledPost` objects
- `src/core/content_processor.py` — Orchestrator: enhance → translate → post
- `src/platforms/` — Facebook, Instagram, LinkedIn, Threads, Twitter publishers
- `src/api/routes/pipeline.py` — Existing FastAPI routes for HOLUS integration

### Deliverables

Create `mcp_server/` with:

```
mcp_server/
├── __init__.py
├── __main__.py        # Entry point: python -m mcp_server
├── server.py          # MCP server (JSON-RPC over stdio)
└── tools.py           # Tool definitions and handlers
```

### MCP Tools to Expose

1. **`post_to_platform`**
   - Params: `text: str`, `platforms: list[str]` (twitter|instagram|linkedin|facebook|threads), `image_url: str|None`
   - Action: Use `ContentProcessor` to post to specified platforms
   - Returns: `{success: bool, results: [{platform, post_id, url, error}]}`

2. **`get_scheduled_posts`**
   - Params: `limit: int = 10`, `platform: str|None`
   - Action: Query scheduler for upcoming posts
   - Returns: `{posts: [{id, text, platform, scheduled_time}]}`

3. **`enhance_text`**
   - Params: `text: str`, `content_type: str = "tweet"` (tweet|post|article)
   - Action: Use `TextEnhancer` to improve text for social media
   - Returns: `{enhanced: str, label: str, emotions: list, character_count: int}`

4. **`translate`**
   - Params: `text: str`, `target_lang: str = "ES"`, `source_lang: str = "EN"`
   - Action: Use `Translator` for DeepL translation
   - Returns: `{translated: str, source_lang: str, target_lang: str}`

### Implementation Notes

- Use `mcp` Python SDK (`pip install mcp`)
- JSON-RPC 2.0 over stdio (standard MCP transport)
- Import from `src.*` modules — add parent to sys.path
- Load env from `.env` file (same as main app)
- Add `"social-media-auto"` server config example for Claude Desktop

### Acceptance Criteria

- [ ] `python -m mcp_server` starts and accepts JSON-RPC on stdio
- [ ] All 4 tools listed via `tools/list`
- [ ] `enhance_text` tool returns enhanced text
- [ ] `translate` tool returns translated text
- [ ] Claude Desktop config snippet provided in README

---

## Task 2: Manager Agent Skeleton

**Status:** In Progress  
**Repo:** `~/.openclaw/workspace/github/holus`  
**Create:** `src/agents/manager.py`  
**Estimated:** 4h  

### Deliverables

```
src/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── base.py          # BaseAgent class
│   └── manager.py       # ManagerAgent
└── config.py            # Paths, constants
```

### ManagerAgent Class

```python
class ManagerAgent(BaseAgent):
    def __init__(self, workspace_root: str = "~/.openclaw/workspace")
    
    async def spawn_agent(self, label: str, model: str, task_prompt: str) -> str:
        """Spawn a sub-agent via OpenClaw CLI. Returns session ID."""
        # Uses: openclaw sessions spawn --model <model> --label <label> --prompt <task_prompt>
    
    async def assign_task(self, task_spec: dict, output_path: str) -> None:
        """Write task spec to a markdown file for agent consumption."""
    
    async def check_status(self, session_id: str) -> dict:
        """Check sub-agent session status. Returns {status, last_output}."""
        # Uses: openclaw sessions status <session_id>
    
    async def update_backlog(self, task_name: str, new_status: str) -> None:
        """Update BACKLOG.md — find task row, change status column."""
        # Read file, regex replace status for matching task, write back
    
    async def run_cycle(self, tasks: list[dict]) -> list[str]:
        """Execute a planning cycle: write specs, spawn builders, track."""
```

### BaseAgent Class

```python
class BaseAgent:
    def __init__(self, name: str, workspace: str)
    
    @property
    def holus_root(self) -> Path
    
    @property  
    def backlog_path(self) -> Path
    
    async def run_command(self, cmd: str) -> tuple[int, str, str]:
        """Run shell command, return (returncode, stdout, stderr)."""
    
    def log(self, msg: str) -> None:
        """Append to daily build log."""
```

### Acceptance Criteria

- [ ] `from src.agents.manager import ManagerAgent` works
- [ ] `spawn_agent()` calls openclaw CLI correctly
- [ ] `update_backlog()` modifies BACKLOG.md in-place
- [ ] Basic test: `python -c "from src.agents.manager import ManagerAgent; print('OK')"`

---

## Task 3: Dashboard v1 — Agent Status View

**Status:** In Progress  
**Repo:** `~/.openclaw/workspace/github/holus`  
**Create:** `src/dashboard/`  
**Port:** 3459  
**Estimated:** 4h  

### Deliverables

```
src/
└── dashboard/
    ├── __init__.py
    ├── app.py           # FastAPI app
    ├── routes.py        # API routes
    └── templates/
        └── index.html   # Single-page dashboard
```

### Dashboard Sections

1. **Agent Status** — List running cron jobs from `openclaw cron list`, show label/schedule/last-run
2. **Recent Build Logs** — Read last 5 files from `~/.openclaw/workspace/memory/` sorted by date
3. **Backlog Summary** — Parse `BACKLOG.md`, show task table with status badges

### API Endpoints

- `GET /` — Serve HTML dashboard
- `GET /api/agents` — JSON: running agents/crons
- `GET /api/logs` — JSON: recent build logs
- `GET /api/backlog` — JSON: parsed backlog

### Tech

- FastAPI + Jinja2 templates
- Tailwind CSS via CDN
- Auto-refresh every 30s via JS
- No database — reads files and CLI output directly

### Acceptance Criteria

- [ ] `uvicorn src.dashboard.app:app --port 3459` starts
- [ ] Dashboard loads at `http://localhost:3459`
- [ ] Shows backlog tasks with status
- [ ] Shows recent memory/log files
