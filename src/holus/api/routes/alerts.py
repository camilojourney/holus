"""Alerts routes — GET /api/v1/alerts.

Score regression, consecutive failures, stall detection.
Reads eval_history.jsonl and checks for anomalies.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

_DEFAULT_EVAL_PATH = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "github"
    / "~Projects"
    / "core"
    / "verification"
    / "eval_history.jsonl"
)

EVAL_HISTORY_PATH = Path(os.environ.get("EVAL_HISTORY_PATH", str(_DEFAULT_EVAL_PATH)))


# -- Models ------------------------------------------------------------------


class Alert(BaseModel):
    """A single alert."""

    type: str  # SCORE_REGRESSION, CONSECUTIVE_FAILURES, STALL
    severity: str  # WARNING, CRITICAL
    skill: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SkillTrend(BaseModel):
    """Per-skill score trend."""

    skill: str
    total_runs: int
    avg_score: float
    last_score: float
    min_score: float
    max_score: float
    rolling_7d: list[dict[str, Any]] = Field(default_factory=list)


class AlertsResponse(BaseModel):
    """Response from the alerts endpoint."""

    alerts: list[Alert]
    trends: list[SkillTrend]
    checked_at: datetime


# -- Logic -------------------------------------------------------------------


def _load_entries() -> list[dict[str, Any]]:
    """Load eval_history.jsonl entries."""
    if not EVAL_HISTORY_PATH.exists():
        return []
    entries = []
    for line in EVAL_HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _check_score_regression(
    entries: list[dict[str, Any]],
    skill_filter: str = "",
) -> list[Alert]:
    """Score drops > 10 points below 7-day rolling average."""
    alerts: list[Alert] = []
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for e in entries:
        skill = e.get("phase") or e.get("workflow") or "unknown"
        if skill_filter and skill.lower() != skill_filter.lower():
            continue
        by_skill[skill].append(e)

    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    for skill, skill_entries in by_skill.items():
        if len(skill_entries) < 3:
            continue

        recent: list[float] = []
        for e in skill_entries:
            try:
                ts_str = str(e["timestamp"]).replace("Z", "+00:00")
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if ts > week_ago:
                    recent.append(float(e["score"]))
            except (KeyError, ValueError):
                continue

        if len(recent) < 2:
            continue

        avg = sum(recent) / len(recent)
        last = recent[-1]

        if last < avg - 10:
            alerts.append(
                Alert(
                    type="SCORE_REGRESSION",
                    severity="WARNING",
                    skill=skill,
                    message=f"{skill}: last score {last:.0f} is {avg - last:.0f}pts below 7-day avg ({avg:.0f})",
                    details={
                        "last_score": last,
                        "rolling_avg": round(avg, 1),
                        "delta": round(last - avg, 1),
                    },
                )
            )

    return alerts


def _check_consecutive_failures(
    entries: list[dict[str, Any]],
    skill_filter: str = "",
    threshold: float = 70,
) -> list[Alert]:
    """3+ consecutive scores below threshold."""
    alerts: list[Alert] = []
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for e in entries:
        skill = e.get("phase") or e.get("workflow") or "unknown"
        if skill_filter and skill.lower() != skill_filter.lower():
            continue
        by_skill[skill].append(e)

    for skill, skill_entries in by_skill.items():
        consecutive = 0
        for e in reversed(skill_entries):
            if e.get("score", 100) < threshold:
                consecutive += 1
            else:
                break

        if consecutive >= 3:
            alerts.append(
                Alert(
                    type="CONSECUTIVE_FAILURES",
                    severity="CRITICAL",
                    skill=skill,
                    message=f"{skill}: {consecutive} consecutive scores below {threshold}",
                    details={"consecutive_count": consecutive, "threshold": threshold},
                )
            )

    return alerts


def _check_stalls(entries: list[dict[str, Any]], skill_filter: str = "") -> list[Alert]:
    """Score 0 = likely stall/empty output."""
    alerts: list[Alert] = []
    for e in reversed(entries[-20:]):
        skill = e.get("phase") or e.get("workflow") or "unknown"
        if skill_filter and skill.lower() != skill_filter.lower():
            continue
        if e.get("score", 100) == 0:
            alerts.append(
                Alert(
                    type="STALL",
                    severity="CRITICAL",
                    skill=skill,
                    message=f"{skill}: score 0 (likely stall/empty output)",
                    details={"cid": e.get("cid", "unknown")},
                )
            )
    return alerts


def _compute_trends(entries: list[dict[str, Any]], skill_filter: str = "") -> list[SkillTrend]:
    """Per-skill score trends with 7-day rolling data."""
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        skill = e.get("phase") or e.get("workflow") or "unknown"
        if skill_filter and skill.lower() != skill_filter.lower():
            continue
        by_skill[skill].append(e)

    trends: list[SkillTrend] = []
    now = datetime.now(UTC)

    for skill, skill_entries in sorted(by_skill.items()):
        scores = [float(e["score"]) for e in skill_entries if "score" in e]
        if not scores:
            continue

        # 7-day rolling data points
        rolling_7d: list[dict[str, Any]] = []
        for i in range(6, -1, -1):
            target_date = (now - timedelta(days=i)).date()
            day_scores: list[float] = []
            for e in skill_entries:
                try:
                    ts_str = str(e["timestamp"]).replace("Z", "+00:00")
                    ts = datetime.fromisoformat(ts_str)
                    if ts.date() == target_date and "score" in e:
                        day_scores.append(float(e["score"]))
                except (KeyError, ValueError):
                    continue
            rolling_7d.append(
                {
                    "date": target_date.isoformat(),
                    "avg_score": round(sum(day_scores) / len(day_scores), 1) if day_scores else 0.0,
                    "count": len(day_scores),
                }
            )

        trends.append(
            SkillTrend(
                skill=skill,
                total_runs=len(scores),
                avg_score=round(sum(scores) / len(scores), 1),
                last_score=scores[-1],
                min_score=min(scores),
                max_score=max(scores),
                rolling_7d=rolling_7d,
            )
        )

    return trends


# -- Endpoints ---------------------------------------------------------------


@router.get("", response_model=AlertsResponse)
async def get_alerts(
    skill: str | None = Query(default=None, description="Filter by skill name"),
) -> AlertsResponse:
    """Check for score regressions, consecutive failures, and stalls."""
    entries = _load_entries()
    skill_filter = skill or ""

    all_alerts: list[Alert] = []
    all_alerts.extend(_check_score_regression(entries, skill_filter))
    all_alerts.extend(_check_consecutive_failures(entries, skill_filter))
    all_alerts.extend(_check_stalls(entries, skill_filter))

    trends = _compute_trends(entries, skill_filter)

    return AlertsResponse(
        alerts=all_alerts,
        trends=trends,
        checked_at=datetime.now(UTC),
    )
