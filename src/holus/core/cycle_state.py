"""Cycle state machine for the Holus agent loop.

Every marketing cycle transitions through well-defined states. Each transition
is logged to trajectory.jsonl so failures are always recoverable and auditable.

States::

    STARTING → HEALTH_CHECK → LOADING_STATE → OBSERVING → REASONING
             → CREATING → QUALITY_CHECK → POSTING → IMPROVING → SAVING_STATE → DONE
                                         ↘ any state can transition to FAILED

Usage::

    ctx = CycleContext.new()
    ctx.transition(CycleState.HEALTH_CHECK)
    ctx.transition(CycleState.OBSERVING)
    # ... work happens ...
    ctx.transition(CycleState.DONE)
    write_trajectory_entry(ctx)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import structlog

logger = structlog.get_logger()

_TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")


# ---------------------------------------------------------------------------
# CycleState enum
# ---------------------------------------------------------------------------


class CycleState(StrEnum):
    """All valid states in a Holus marketing cycle."""

    STARTING = "starting"
    HEALTH_CHECK = "health_check"
    LOADING_STATE = "loading_state"
    OBSERVING = "observing"
    REASONING = "reasoning"
    CREATING = "creating"
    QUALITY_CHECK = "quality_check"
    POSTING = "posting"
    IMPROVING = "improving"
    SAVING_STATE = "saving_state"
    DONE = "done"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# HealthResult (imported here to avoid circular imports; also used in health.py)
# ---------------------------------------------------------------------------


@dataclass
class HealthResult:
    """Result of a preflight health check.

    Attributes:
        blocking_ok: False means the cycle must not proceed.
        available_silos: Silos that passed their health checks and can be called.
        warnings: Non-fatal issues to log but not block on.
    """

    blocking_ok: bool
    available_silos: list[str]
    warnings: list[str]


# ---------------------------------------------------------------------------
# CycleContext
# ---------------------------------------------------------------------------


@dataclass
class CycleContext:
    """Mutable state for a single agent cycle.

    Created at cycle start. Passed through every phase. Written to
    trajectory.jsonl at DONE or FAILED.

    Attributes:
        cycle_id: ISO 8601 UTC timestamp string. Used as the unique key in
            trajectory.jsonl. Format: ``"2026-03-12T14:30:00.000000+00:00"``.
        current_state: The cycle's current CycleState.
        health_result: Set after HEALTH_CHECK completes.
        content_created: Count of content items successfully created.
        content_posted: Count of content items successfully posted.
        content_failed: Count of content items that failed creation or posting.
        quality_scores: Per-item quality scores, each in [0.0, 1.0].
        capability_gaps: Descriptions of missing tools or skills encountered.
        error: Error message if the cycle ended in FAILED state.
        duration_seconds: Wall-clock seconds from start to DONE/FAILED.
        started_at: UTC datetime when the cycle was created.
        trajectory_path: Path to the trajectory log file.
    """

    cycle_id: str
    current_state: CycleState
    health_result: HealthResult | None = None
    content_created: int = 0
    content_posted: int = 0
    content_failed: int = 0
    quality_scores: list[float] = field(default_factory=list)
    capability_gaps: list[str] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trajectory_path: Path = field(default_factory=lambda: _TRAJECTORY_PATH)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def new(cls, trajectory_path: Path | None = None) -> CycleContext:
        """Create a new CycleContext with a unique cycle_id."""
        now = datetime.now(UTC)
        return cls(
            cycle_id=now.isoformat(),
            current_state=CycleState.STARTING,
            started_at=now,
            trajectory_path=trajectory_path or _TRAJECTORY_PATH,
        )

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def transition(self, new_state: CycleState) -> None:
        """Transition to a new state, logging the event to trajectory.jsonl.

        Logs every transition immediately so partial cycles are visible
        even if the process crashes before the cycle completes.

        Args:
            new_state: The state to transition to.
        """
        old_state = self.current_state
        self.current_state = new_state

        logger.info(
            "Cycle state transition",
            cycle_id=self.cycle_id,
            from_state=old_state,
            to_state=new_state,
        )

        # Write a lightweight transition record to the trajectory log.
        entry: dict[str, object] = {
            "cycle_id": self.cycle_id,
            "event": "transition",
            "from_state": str(old_state),
            "to_state": str(new_state),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _append_jsonl(self.trajectory_path, entry)

    # ------------------------------------------------------------------
    # Duration helper
    # ------------------------------------------------------------------

    def finish(self) -> None:
        """Record the elapsed duration. Call before writing the final entry."""
        self.duration_seconds = (datetime.now(UTC) - self.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Trajectory writer
# ---------------------------------------------------------------------------


def write_trajectory_entry(context: CycleContext) -> None:
    """Write the final cycle summary to trajectory.jsonl.

    Called at DONE or FAILED. Creates the directory if it does not exist.
    Appends; never overwrites existing entries.

    The written format::

        {
          "cycle_id": "2026-03-12T14:30:00+00:00",
          "phase": "done",
          "health": {"blocking_ok": true, "available_silos": [...], "warnings": [...]},
          "content_created": 2,
          "content_posted": 2,
          "content_failed": 0,
          "quality_scores": [0.87, 0.92],
          "capability_gaps": [],
          "duration_seconds": 142.3,
          "error": null
        }

    Args:
        context: The completed (or failed) CycleContext.
    """
    if context.duration_seconds is None:
        context.finish()

    health_dict: dict[str, object] | None = None
    if context.health_result is not None:
        health_dict = {
            "blocking_ok": context.health_result.blocking_ok,
            "available_silos": context.health_result.available_silos,
            "warnings": context.health_result.warnings,
        }

    entry: dict[str, object] = {
        "cycle_id": context.cycle_id,
        "phase": str(context.current_state),
        "health": health_dict,
        "content_created": context.content_created,
        "content_posted": context.content_posted,
        "content_failed": context.content_failed,
        "quality_scores": context.quality_scores,
        "capability_gaps": context.capability_gaps,
        "duration_seconds": context.duration_seconds,
        "error": context.error,
    }
    _append_jsonl(context.trajectory_path, entry)

    logger.info(
        "Trajectory entry written",
        cycle_id=context.cycle_id,
        phase=str(context.current_state),
        content_posted=context.content_posted,
        error=context.error,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _append_jsonl(path: Path, entry: dict[str, object]) -> None:
    """Append a JSON object as a single line to *path*.

    Creates intermediate directories if they do not exist.
    On write failure, attempts to write to a ``.failed`` fallback file and
    logs a warning. If the fallback also fails, the entry is printed to
    stderr so data is never silently lost.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning(
            "Failed to write trajectory entry",
            path=str(path),
            error=str(exc),
        )
        # Fallback: write to stderr so data is never silently lost
        import sys

        try:
            fallback = path.parent / f"{path.stem}.failed{path.suffix}"
            with fallback.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info("Trajectory entry written to fallback", fallback=str(fallback))
        except OSError:
            print(json.dumps(entry, ensure_ascii=False), file=sys.stderr)
