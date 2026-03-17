"""Self-improvement dashboard API routes.

Provides observability into the autonomous improvement loop:
- Score trends (judge + engagement over time)
- Thompson Sampling arm performance
- Prompt population status
- Gap detection summary
- Drift alerts
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/improvement", tags=["self-improvement"])

TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
BANDIT_ARMS_PATH = Path(".self-improvement/bandit_arms.json")
CAPABILITY_GAPS_DIR = Path(".self-improvement/capability-requests")
KNOWLEDGE_GAPS_DIR = Path(".self-improvement/knowledge/requests")


def _read_trajectory(days: int = 30) -> list[dict[str, Any]]:
    """Read recent trajectory entries."""
    if not TRAJECTORY_PATH.exists():
        return []

    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    entries: list[dict[str, Any]] = []

    with open(TRAJECTORY_PATH, encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line.strip())
                if entry.get("timestamp", "") >= cutoff:
                    entries.append(entry)
            except (json.JSONDecodeError, AttributeError):
                continue

    return entries


@router.get("/score-trends")
async def score_trends(days: int = 30) -> dict[str, Any]:
    """Score trends over time — judge and engagement scores by day."""
    entries = _read_trajectory(days)

    daily: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"judge": [], "engagement": [], "reward": []})

    for e in entries:
        date = e.get("timestamp", "")[:10]
        if not date:
            continue

        if e.get("judge_score") is not None:
            daily[date]["judge"].append(e["judge_score"])

        meta = e.get("metadata", {})
        if meta.get("engagement_signal") is not None:
            daily[date]["engagement"].append(meta["engagement_signal"])
        if meta.get("blended_reward") is not None:
            daily[date]["reward"].append(meta["blended_reward"])

    trends = []
    for date in sorted(daily):
        d = daily[date]
        trends.append({
            "date": date,
            "avg_judge_score": round(sum(d["judge"]) / len(d["judge"]), 3) if d["judge"] else None,
            "avg_engagement": round(sum(d["engagement"]) / len(d["engagement"]), 3) if d["engagement"] else None,
            "avg_reward": round(sum(d["reward"]) / len(d["reward"]), 3) if d["reward"] else None,
            "n_judge": len(d["judge"]),
            "n_engagement": len(d["engagement"]),
        })

    return {"days": days, "trends": trends, "total_entries": len(entries)}


@router.get("/bandit-arms")
async def bandit_arms() -> dict[str, Any]:
    """Thompson Sampling arm performance."""
    if not BANDIT_ARMS_PATH.exists():
        return {"arms": [], "total_observations": 0}

    try:
        data = json.loads(BANDIT_ARMS_PATH.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return {"arms": [], "total_observations": 0, "error": "Failed to load arms"}


@router.get("/gaps")
async def gaps() -> dict[str, Any]:
    """Open capability and knowledge gaps."""
    capability_gaps: list[dict[str, str]] = []
    if CAPABILITY_GAPS_DIR.exists():
        for path in CAPABILITY_GAPS_DIR.glob("*.md"):
            capability_gaps.append({
                "file": path.name,
                "size": str(path.stat().st_size),
            })

    knowledge_gaps: list[dict[str, str]] = []
    if KNOWLEDGE_GAPS_DIR.exists():
        for path in KNOWLEDGE_GAPS_DIR.glob("*.md"):
            if path.name == "README.md":
                continue
            knowledge_gaps.append({
                "file": path.name,
                "size": str(path.stat().st_size),
            })

    return {
        "capability_gaps": capability_gaps,
        "knowledge_gaps": knowledge_gaps,
        "total": len(capability_gaps) + len(knowledge_gaps),
    }


@router.get("/drift")
async def drift_check(days: int = 30) -> dict[str, Any]:
    """Check for score drift across agents."""
    entries = _read_trajectory(days)

    # Group by agent_id
    agent_scores: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in entries:
        if e.get("judge_score") is not None:
            agent_scores[e.get("agent_id", "unknown")].append(
                (e.get("timestamp", ""), e["judge_score"])
            )

    alerts: list[dict[str, Any]] = []
    for agent_id, scores in agent_scores.items():
        if len(scores) < 5:
            continue
        values = [s for _, s in scores]
        peak = max(values)
        avg = sum(values) / len(values)
        if peak - avg >= 0.1:
            alerts.append({
                "agent_id": agent_id,
                "peak_score": round(peak, 3),
                "avg_score": round(avg, 3),
                "drift": round(peak - avg, 3),
                "n_observations": len(scores),
                "status": "DRIFTING",
            })

    return {
        "alerts": alerts,
        "agents_checked": len(agent_scores),
        "total_observations": sum(len(v) for v in agent_scores.values()),
    }


@router.get("/summary")
async def improvement_summary() -> dict[str, Any]:
    """Complete self-improvement status dashboard."""
    entries = _read_trajectory(30)

    # Count by type
    judge_scored = sum(1 for e in entries if e.get("judge_score") is not None)
    engagement_scored = sum(1 for e in entries if e.get("metadata", {}).get("engagement_signal") is not None)
    paired = sum(
        1 for e in entries
        if e.get("judge_score") is not None and e.get("metadata", {}).get("engagement_signal") is not None
    )

    # Activation gates status
    import contextlib

    bandit_data = {}
    if BANDIT_ARMS_PATH.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            bandit_data = json.loads(BANDIT_ARMS_PATH.read_text(encoding="utf-8"))

    total_bandit_obs = bandit_data.get("total_observations", 0)

    return {
        "trajectory_entries_30d": len(entries),
        "judge_scored": judge_scored,
        "engagement_scored": engagement_scored,
        "paired_observations": paired,
        "activation_gates": {
            "thompson_sampling": {
                "threshold": 30,
                "current": total_bandit_obs,
                "active": total_bandit_obs >= 30,
            },
            "prompt_evolution": {
                "threshold": 500,
                "current": len(entries),
                "active": len(entries) >= 500,
            },
            "blended_reward": {
                "threshold": 100,
                "current": paired,
                "active": paired >= 100,
            },
        },
    }
