"""Health and metrics routes — GET /api/v1/health, /metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from fastapi import APIRouter

from holus.api.models import HealthStatus, KPIMetrics
from holus.api.routes.evaluations import EVAL_HISTORY_PATH
from holus.api.routes.trajectory import TRAJECTORY_PATH, _load_trajectory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
AGENTS_YAML = REPO_ROOT / "agents" / "AGENTS.yaml"
GUARDRAILS_YAML = REPO_ROOT / "config" / "guardrails.yaml"
CONTENT_QUEUE_DIR = REPO_ROOT / "data" / "content-queue"


def _is_kill_switch_active() -> bool:
    """Check guardrails.yaml for kill_switch state.

    The kill switch is Redis-backed in production. For the Observatory API
    (read-only, file-based), we check guardrails.yaml for a static override.
    If guardrails.yaml has kill_switch.active: true, we report it as active.
    Otherwise, we assume not active (Redis not required for this API).
    """
    if not GUARDRAILS_YAML.exists():
        return False
    try:
        data = yaml.safe_load(GUARDRAILS_YAML.read_text(encoding="utf-8"))
        ks = data.get("kill_switch", {})
        return bool(ks.get("active", False))
    except Exception as exc:
        logger.warning("Failed to read guardrails.yaml: %s", exc)
        return False


def _count_content_queue() -> int:
    """Count YAML and JSON files in the content queue directory."""
    if not CONTENT_QUEUE_DIR.exists():
        return 0
    return len(list(CONTENT_QUEUE_DIR.glob("*.yaml"))) + len(list(CONTENT_QUEUE_DIR.glob("*.json")))


def _error_rate_last_hour() -> float | None:
    """Compute fraction of trajectory entries with error outcome in the last hour."""
    entries = _load_trajectory()
    if not entries:
        return None

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=1)

    recent = []
    for e in entries:
        raw_ts = e.get("timestamp")
        if raw_ts is None:
            continue
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff:
                recent.append(e)
        except (ValueError, TypeError):
            continue

    if not recent:
        return None

    errors = sum(1 for e in recent if e.get("outcome") == "error")
    return errors / len(recent)


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    """Return system health status."""
    if not TRAJECTORY_PATH.exists():
        logger.warning("trajectory.jsonl not found at %s", TRAJECTORY_PATH)
    if not EVAL_HISTORY_PATH.exists():
        logger.warning("eval_history.jsonl not found at %s", EVAL_HISTORY_PATH)
    if not AGENTS_YAML.exists():
        logger.warning("AGENTS.yaml not found at %s", AGENTS_YAML)

    return HealthStatus(
        kill_switch_active=_is_kill_switch_active(),
        trajectory_file_exists=TRAJECTORY_PATH.exists(),
        eval_history_file_exists=EVAL_HISTORY_PATH.exists(),
        agents_yaml_exists=AGENTS_YAML.exists(),
        content_queue_count=_count_content_queue(),
        error_rate_1h=_error_rate_last_hour(),
    )


@router.get("/metrics", response_model=KPIMetrics)
async def metrics() -> KPIMetrics:
    """Return KPI dashboard metrics aggregated from trajectory and content."""
    entries = _load_trajectory()
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    total_cycles = len(entries)
    successes = sum(1 for e in entries if e.get("outcome") == "success")
    success_rate = (successes / total_cycles) if total_cycles > 0 else 0.0

    quality_scores = [e["quality_score"] for e in entries if e.get("quality_score") is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    costs = [e["cost_usd"] for e in entries if e.get("cost_usd") is not None]
    total_cost = sum(costs) if costs else None

    # Active agents in last 24h
    active_agents: set[str] = set()
    for e in entries:
        raw_ts = e.get("timestamp")
        if raw_ts is None:
            continue
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff_24h:
                agent = e.get("agent_id")
                if agent:
                    active_agents.add(agent)
        except (ValueError, TypeError):
            continue

    # Content published in last 7d
    published_7d = 0
    for e in entries:
        if e.get("outcome") != "success":
            continue
        raw_ts = e.get("timestamp")
        if raw_ts is None:
            continue
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff_7d and e.get("action") in ("publish", "published"):
                published_7d += 1
        except (ValueError, TypeError):
            continue

    # Cost per approved asset
    approved_count = sum(
        1 for e in entries if e.get("action") in ("publish", "published", "approve")
    )
    cost_per_asset: float | None = None
    if total_cost is not None and approved_count > 0:
        cost_per_asset = total_cost / approved_count

    return KPIMetrics(
        total_cycles=total_cycles,
        success_rate=success_rate,
        avg_quality_score=avg_quality,
        total_cost_usd=total_cost,
        cost_per_approved_asset=cost_per_asset,
        active_agents_24h=len(active_agents),
        content_published_7d=published_7d,
    )
