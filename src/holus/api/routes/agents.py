"""Agent registry routes — GET /api/v1/agents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from holus.api.models import AgentInfo, AgentMetrics
from holus.api.routes.trajectory import _load_trajectory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
AGENTS_YAML = REPO_ROOT / "agents" / "AGENTS.yaml"


def _load_agents_yaml() -> dict[str, Any]:
    """Load agents/AGENTS.yaml and return the agents dict."""
    if not AGENTS_YAML.exists():
        raise HTTPException(status_code=503, detail="agents registry unavailable")
    try:
        data = yaml.safe_load(AGENTS_YAML.read_text(encoding="utf-8"))
        return data.get("agents", {})
    except Exception as exc:
        logger.warning("Failed to parse AGENTS.yaml: %s", exc)
        raise HTTPException(status_code=503, detail="agents registry unavailable") from exc


def _build_agent_info(agent_id: str, meta: dict[str, Any], entries: list[dict[str, Any]]) -> AgentInfo:
    """Build AgentInfo from AGENTS.yaml metadata and trajectory entries."""
    now = datetime.now(UTC)
    cutoff_7d = now - timedelta(days=7)

    # Filter entries for this agent
    agent_entries = [e for e in entries if e.get("agent_id") == agent_id]

    # Last run info
    last_run: datetime | None = None
    last_status: str | None = None
    run_count_7d = 0

    for entry in agent_entries:
        raw_ts = entry.get("timestamp")
        if raw_ts is None:
            continue
        try:
            if isinstance(raw_ts, str):
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
            else:
                continue
        except (ValueError, TypeError):
            continue

        if last_run is None or ts > last_run:
            last_run = ts
            last_status = entry.get("outcome")

        if ts >= cutoff_7d:
            run_count_7d += 1

    model_tier = meta.get("model_tier", "operational")
    model_map = {
        "strategic": "claude-opus-4-6",
        "operational": "claude-sonnet-4-6",
        "classification": "claude-haiku-4-5-20251001",
    }
    model = model_map.get(model_tier, model_tier)

    return AgentInfo(
        id=agent_id,
        name=meta.get("name", agent_id),
        model=model,
        role=meta.get("role", ""),
        last_run=last_run,
        last_status=last_status,
        run_count_7d=run_count_7d,
    )


@router.get("", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """Return all agents from AGENTS.yaml with trajectory-derived metadata."""
    agents_data = _load_agents_yaml()
    trajectory = _load_trajectory()

    result = []
    for agent_id, meta in agents_data.items():
        result.append(_build_agent_info(agent_id, meta, trajectory))
    return result


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str) -> AgentInfo:
    """Return a single agent by ID with full performance history."""
    agents_data = _load_agents_yaml()

    if agent_id not in agents_data:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    trajectory = _load_trajectory()
    return _build_agent_info(agent_id, agents_data[agent_id], trajectory)


@router.get("/{agent_id}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(agent_id: str) -> AgentMetrics:
    """Return aggregated metrics for a single agent."""
    agents_data = _load_agents_yaml()

    if agent_id not in agents_data:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    trajectory = _load_trajectory()
    agent_entries = [e for e in trajectory if e.get("agent_id") == agent_id]

    total_runs = len(agent_entries)
    successes = sum(1 for e in agent_entries if e.get("outcome") == "success")
    success_rate = (successes / total_runs) if total_runs > 0 else 0.0

    quality_scores = [
        e["quality_score"]
        for e in agent_entries
        if e.get("quality_score") is not None
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    costs = [e["cost_usd"] for e in agent_entries if e.get("cost_usd") is not None]
    avg_cost = sum(costs) / len(costs) if costs else None

    return AgentMetrics(
        agent_id=agent_id,
        avg_quality_score=avg_quality,
        total_runs=total_runs,
        success_rate=success_rate,
        avg_cost_usd=avg_cost,
        p50_latency_s=None,
        p95_latency_s=None,
    )
