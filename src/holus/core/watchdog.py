"""Dead man's switch for the Holus agent loop.

The watchdog reads ``trajectory.jsonl`` and alerts if the loop has been silent
for too long, or if the last N cycles all failed.

Usage::

    result = check_watchdog(trajectory_path, max_silence_hours=2.0)
    if result.alert:
        notify(f"Loop silent for {result.silence_hours:.1f}h: {result.last_error}")

    if consecutive_failure_check(trajectory_path, threshold=3):
        notify("Three consecutive failures — operator review required")
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class WatchdogResult(BaseModel):
    """Result of a watchdog check.

    Attributes:
        alert: True if the silence threshold has been exceeded.
        last_success_at: UTC datetime of the most recent successful cycle
            (phase == "done"), or None if no successful cycle exists.
        last_error: Error message from the most recent failed cycle, or None.
        silence_hours: Hours since the last successful cycle ended.
            Set to ``float("inf")`` when no successful cycle exists.
    """

    alert: bool
    last_success_at: datetime | None
    last_error: str | None
    silence_hours: float


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def check_watchdog(
    trajectory_path: Path,
    max_silence_hours: float = 2.0,
) -> WatchdogResult:
    """Check whether the agent loop has gone silent.

    Reads ``trajectory_path`` and finds the most recent **summary** entry
    (one with a ``"phase"`` key). A summary entry is written at cycle DONE or
    FAILED. If the last successful summary (``phase == "done"``) is older than
    ``max_silence_hours``, returns ``alert=True``.

    Args:
        trajectory_path: Path to ``trajectory.jsonl``.
        max_silence_hours: Maximum acceptable hours without a successful cycle.
            Defaults to 2.0.

    Returns:
        :class:`WatchdogResult` with alert status, timing, and last error.
    """
    summaries = _load_summaries(trajectory_path)

    if not summaries:
        # No trajectory at all — could be a fresh install; return alert with inf silence.
        logger.info("watchdog: no trajectory entries found", path=str(trajectory_path))
        return WatchdogResult(
            alert=True,
            last_success_at=None,
            last_error=None,
            silence_hours=float("inf"),
        )

    # Find the most recent error for context.
    last_error: str | None = None
    for entry in reversed(summaries):
        if entry.get("error"):
            last_error = str(entry["error"])
            break

    # Find the most recent successful cycle.
    last_success_at: datetime | None = None
    for entry in reversed(summaries):
        if entry.get("phase") == "done":
            last_success_at = _parse_cycle_timestamp(entry)
            break

    if last_success_at is None:
        # All entries are failures — maximum silence.
        logger.warning("watchdog: no successful cycle found", last_error=last_error)
        return WatchdogResult(
            alert=True,
            last_success_at=None,
            last_error=last_error,
            silence_hours=float("inf"),
        )

    now = datetime.now(UTC)
    silence_hours = (now - last_success_at).total_seconds() / 3600.0
    alert = silence_hours > max_silence_hours

    logger.info(
        "watchdog check complete",
        alert=alert,
        silence_hours=round(silence_hours, 2),
        max_silence_hours=max_silence_hours,
        last_success_at=last_success_at.isoformat(),
    )

    return WatchdogResult(
        alert=alert,
        last_success_at=last_success_at,
        last_error=last_error,
        silence_hours=silence_hours,
    )


def consecutive_failure_check(
    trajectory_path: Path,
    threshold: int = 3,
) -> bool:
    """Return True if the last *threshold* cycles all failed.

    Only summary entries (those with a ``"phase"`` key) are considered.
    If there are fewer than ``threshold`` summary entries, returns False.

    Args:
        trajectory_path: Path to ``trajectory.jsonl``.
        threshold: Number of consecutive failures that triggers True.

    Returns:
        True if the last ``threshold`` summary entries all have ``phase == "failed"``.
    """
    summaries = _load_summaries(trajectory_path)

    if len(summaries) < threshold:
        return False

    recent = summaries[-threshold:]
    all_failed = all(entry.get("phase") == "failed" for entry in recent)

    if all_failed:
        logger.warning(
            "consecutive_failure_check: threshold exceeded",
            threshold=threshold,
            recent_phases=[e.get("phase") for e in recent],
        )

    return all_failed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_summaries(trajectory_path: Path) -> list[dict[str, Any]]:
    """Read trajectory.jsonl and return only summary entries (those with 'phase' key)."""
    if not trajectory_path.exists():
        return []

    summaries: list[dict[str, Any]] = []
    try:
        for line in trajectory_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if "phase" in entry:
                    summaries.append(entry)
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        logger.warning("watchdog: failed to read trajectory", path=str(trajectory_path), error=str(exc))

    return summaries


def _parse_cycle_timestamp(entry: dict[str, Any]) -> datetime | None:
    """Extract a UTC datetime from a trajectory summary entry.

    Tries ``cycle_id`` first (which is an ISO timestamp), then falls back to
    computing ``started_at + duration_seconds`` if available.
    """
    cycle_id = entry.get("cycle_id")
    if cycle_id:
        try:
            dt = datetime.fromisoformat(str(cycle_id))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            # cycle_id is the *start* time; add duration to get end time if available.
            duration = entry.get("duration_seconds")
            if duration is not None:
                from datetime import timedelta
                dt = dt + timedelta(seconds=float(duration))
            return dt
        except ValueError:
            pass

    return None
