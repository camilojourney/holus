"""Trajectory logging: append-only JSONL recording of agent runs.

Every agent execution is recorded as a ``TrajectoryEntry`` in an
append-only JSONL file.  This provides:

  - Full audit trail of what happened and when.
  - Failure streak detection (triggers prompt optimization).
  - Data source for weekly self-improvement reviews.
  - Input for Langfuse dataset construction.

File format:  ``trajectory.jsonl`` -- one JSON object per line.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TrajectoryEntry:
    """A single entry in the trajectory log."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    agent_id: str = ""
    task_type: str = ""
    task_summary: str = ""

    # Execution
    status: Literal["success", "failure", "partial", "error"] = "success"
    duration_seconds: float = 0.0
    attempts: int = 1

    # Quality
    judge_verdict: str | None = None       # PASS / FAIL / PARTIAL
    judge_score: float | None = None       # 0.0 - 1.0
    judge_feedback: str | None = None

    # Cost
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    # Metadata
    thread_id: str | None = None
    correlation_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "task_summary": self.task_summary,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "attempts": self.attempts,
            "judge_verdict": self.judge_verdict,
            "judge_score": self.judge_score,
            "judge_feedback": self.judge_feedback,
            "model_used": self.model_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "thread_id": self.thread_id,
            "correlation_id": self.correlation_id,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrajectoryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class TrajectoryLogger:
    """Append-only JSONL trajectory logger.

    Usage::

        tl = TrajectoryLogger(Path(".self-improvement/memory/trajectory.jsonl"))
        tl.append(TrajectoryEntry(agent_id="trading-agent", ...))

        # Read all entries
        entries = tl.read_all()

        # Detect failure streaks
        streak = tl.failure_streak("trading-agent", task_type="trade_signal")
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: TrajectoryEntry) -> None:
        """Append a single entry to the trajectory file."""
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(entry.to_json() + "\n")
        logger.debug("Trajectory logged: %s/%s -> %s", entry.agent_id, entry.task_type, entry.status)

    def read_all(self) -> list[TrajectoryEntry]:
        """Read all trajectory entries."""
        if not self.path.exists():
            return []

        entries: list[TrajectoryEntry] = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(TrajectoryEntry.from_dict(data))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning("Skipping malformed trajectory line: %s", exc)
        return entries

    def read_filtered(
        self,
        *,
        agent_id: str | None = None,
        task_type: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[TrajectoryEntry]:
        """Read entries matching the given filters (most recent first)."""
        all_entries = self.read_all()

        filtered = all_entries
        if agent_id:
            filtered = [e for e in filtered if e.agent_id == agent_id]
        if task_type:
            filtered = [e for e in filtered if e.task_type == task_type]
        if status:
            filtered = [e for e in filtered if e.status == status]

        # Most recent first
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        if limit:
            filtered = filtered[:limit]

        return filtered

    # -- Failure streak detection --------------------------------------------

    def failure_streak(
        self,
        agent_id: str,
        task_type: str | None = None,
    ) -> int:
        """Count consecutive recent failures for an agent.

        Returns the number of consecutive failures at the tail of the
        trajectory.  A streak of 3+ triggers prompt optimization.
        """
        entries = self.read_filtered(agent_id=agent_id, task_type=task_type)

        streak = 0
        for entry in entries:
            if entry.status in ("failure", "error"):
                streak += 1
            else:
                break  # Streak broken by a success/partial

        return streak

    def needs_optimization(
        self,
        agent_id: str,
        task_type: str | None = None,
        threshold: int = 3,
    ) -> bool:
        """Return ``True`` if the agent has a failure streak >= threshold.

        This is the bridge between Reflexion (per-task) and DSPy (systematic):
        when per-task reflection is not enough, systematic prompt optimization
        is triggered.
        """
        return self.failure_streak(agent_id, task_type) >= threshold

    # -- Statistics ----------------------------------------------------------

    def summary(self, agent_id: str | None = None) -> dict[str, Any]:
        """Return summary statistics for the trajectory log."""
        entries = self.read_filtered(agent_id=agent_id)
        if not entries:
            return {"total": 0}

        statuses = {}
        total_cost = 0.0
        total_tokens = 0
        scores: list[float] = []

        for e in entries:
            statuses[e.status] = statuses.get(e.status, 0) + 1
            total_cost += e.cost_usd
            total_tokens += e.input_tokens + e.output_tokens
            if e.judge_score is not None:
                scores.append(e.judge_score)

        return {
            "total": len(entries),
            "statuses": statuses,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_score": round(sum(scores) / len(scores), 3) if scores else None,
            "min_score": round(min(scores), 3) if scores else None,
            "max_score": round(max(scores), 3) if scores else None,
        }
