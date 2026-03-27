"""Evaluations routes — GET /api/v1/evaluations."""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from holus.api.models import EvaluationResult, EvaluationsResponse, EvaluationSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

PASS_THRESHOLD = 7.0

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


def _load_evaluations() -> list[EvaluationResult]:
    """Load all evaluation entries from eval_history.jsonl."""
    if not EVAL_HISTORY_PATH.exists():
        logger.warning("eval_history.jsonl not found at %s", EVAL_HISTORY_PATH)
        return []

    results: list[EvaluationResult] = []
    for lineno, line in enumerate(
        EVAL_HISTORY_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            raw_ts = raw.get("timestamp")
            if raw_ts is None:
                continue
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)

            score = float(raw.get("score", 0.0))
            max_score = float(raw.get("max_score", 10.0))
            threshold = float(raw.get("pass_threshold", PASS_THRESHOLD))

            results.append(
                EvaluationResult(
                    timestamp=ts,
                    agent_id=str(raw.get("agent_id", "unknown")),
                    score=score,
                    max_score=max_score,
                    pass_threshold=threshold,
                    passed=score >= threshold,
                    notes=raw.get("notes"),
                )
            )
        except Exception as exc:
            logger.warning("Malformed eval entry at line %d: %s", lineno, exc)

    return results


@router.get("", response_model=EvaluationsResponse)
async def list_evaluations(
    agent_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> EvaluationsResponse | JSONResponse:
    """Return evaluation results, optionally filtered by agent."""
    evals = _load_evaluations()

    if agent_id:
        evals = [e for e in evals if e.agent_id == agent_id]

    # Sort newest first, then limit
    evals.sort(key=lambda e: e.timestamp, reverse=True)
    evals = evals[:limit]

    headers = {}
    if not EVAL_HISTORY_PATH.exists():
        headers["X-Data-Source"] = "unavailable"

    if headers:
        return JSONResponse(
            content={"evaluations": [e.model_dump(mode="json") for e in evals]},
            headers=headers,
        )

    return EvaluationsResponse(evaluations=evals)


@router.get("/summary", response_model=EvaluationSummary)
async def get_evaluation_summary() -> EvaluationSummary:
    """Return aggregated evaluation metrics."""
    evals = _load_evaluations()

    if not evals:
        return EvaluationSummary(
            avg_score=0.0,
            pass_rate=0.0,
            score_by_agent={},
            trend_7d=[],
        )

    avg_score = sum(e.score for e in evals) / len(evals)
    pass_rate = sum(1 for e in evals if e.passed) / len(evals)

    # Per-agent averages
    agent_scores: dict[str, list[float]] = defaultdict(list)
    for e in evals:
        agent_scores[e.agent_id].append(e.score)
    score_by_agent = {agent: sum(scores) / len(scores) for agent, scores in agent_scores.items()}

    # 7-day trend
    now = datetime.now(UTC)
    trend_7d = []
    for i in range(6, -1, -1):
        target_date = (now - timedelta(days=i)).date()
        day_evals = [e for e in evals if e.timestamp.date() == target_date]
        day_avg = sum(e.score for e in day_evals) / len(day_evals) if day_evals else 0.0
        trend_7d.append({"date": target_date.isoformat(), "avg_score": day_avg})

    return EvaluationSummary(
        avg_score=avg_score,
        pass_rate=pass_rate,
        score_by_agent=score_by_agent,
        trend_7d=trend_7d,
    )
