"""
Holus Dashboard — FastAPI-based control panel for monitoring and managing agents.

Provides:
- REST API for agent status, run history, and manual triggers
- Server-rendered HTML dashboard with HTMX for live updates
- Health check endpoint for external monitoring

Spec: specs/008-dashboard-api.md
"""
from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator


# --- Validation ---

_AGENT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

_SECRET_KEYWORDS = {"key", "token", "secret", "password", "credential", "sid"}


def _validate_agent_name(name: str) -> str:
    """Validate agent name is alphanumeric + underscore only (EDGE-001)."""
    if not _AGENT_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Agent name must be alphanumeric and underscores only.",
        )
    return name


def _redact_secrets(obj: object, depth: int = 0) -> object:
    """Recursively redact secret values from config dicts (SPEC-003, SPEC-007)."""
    if depth > 20:
        return obj  # guard against pathological nesting
    if isinstance(obj, dict):
        return {
            k: (
                "***REDACTED***"
                if any(kw in k.lower() for kw in _SECRET_KEYWORDS)
                else _redact_secrets(v, depth + 1)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_secrets(item, depth + 1) for item in obj]
    return obj


# --- App factory ---

def create_app(orchestrator: Orchestrator) -> FastAPI:
    """Create the FastAPI app wired to a live orchestrator instance."""

    app = FastAPI(title="Holus Dashboard", version="0.1.0")
    start_time = time.monotonic()

    template_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(template_dir))

    # ------------------------------------------------------------------
    # SPEC-001  Health Check
    # ------------------------------------------------------------------
    @app.get("/api/health")
    async def health() -> JSONResponse:
        scheduler_ok = orchestrator.scheduler.running
        body = {
            "status": "ok" if scheduler_ok else "degraded",
            "uptime_seconds": int(time.monotonic() - start_time),
            "agent_count": len(orchestrator.agents),
        }
        status_code = 200 if scheduler_ok else 503
        return JSONResponse(content=body, status_code=status_code)

    # ------------------------------------------------------------------
    # SPEC-002  Agent List
    # ------------------------------------------------------------------
    @app.get("/api/agents")
    async def list_agents():
        return [agent.get_status() for agent in orchestrator.agents.values()]

    # ------------------------------------------------------------------
    # SPEC-003  Agent Detail
    # ------------------------------------------------------------------
    @app.get("/api/agents/{agent_name}")
    async def agent_detail(agent_name: str):
        name = _validate_agent_name(agent_name)
        agent = orchestrator.agents.get(name)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_config = orchestrator.config.get("agents", {}).get(name, {})

        return {
            **agent.get_status(),
            "config": _redact_secrets(agent_config),
            "recent_runs": agent.get_run_history(limit=10),
        }

    # ------------------------------------------------------------------
    # SPEC-004  Manual Run
    # ------------------------------------------------------------------
    @app.post("/api/agents/{agent_name}/run", status_code=202)
    async def trigger_run(agent_name: str):
        name = _validate_agent_name(agent_name)
        agent = orchestrator.agents.get(name)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        if agent._is_running:
            raise HTTPException(status_code=409, detail="Agent is already running")

        # Fire-and-forget async task
        asyncio.create_task(agent.scheduled_run())
        return {"status": "started", "agent": name}

    # ------------------------------------------------------------------
    # SPEC-006  Run History
    # ------------------------------------------------------------------
    @app.get("/api/agents/{agent_name}/runs")
    async def run_history(
        agent_name: str,
        limit: int = Query(default=20, ge=1, le=100),
    ):
        name = _validate_agent_name(agent_name)
        agent = orchestrator.agents.get(name)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent.get_run_history(limit=limit)

    # ------------------------------------------------------------------
    # SPEC-007  Agent Config
    # ------------------------------------------------------------------
    @app.get("/api/agents/{agent_name}/config")
    async def agent_config(agent_name: str):
        name = _validate_agent_name(agent_name)
        if name not in orchestrator.agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        raw = orchestrator.config.get("agents", {}).get(name, {})
        return _redact_secrets(raw)

    # ------------------------------------------------------------------
    # SPEC-005  Dashboard HTML
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        agents = [agent.get_status() for agent in orchestrator.agents.values()]
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "agents": agents,
                "agent_count": len(agents),
                "uptime_seconds": int(time.monotonic() - start_time),
            },
        )

    return app
