"""Dead man's switch for stalled marketing cycles."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
_SUCCESS_THRESHOLD = timedelta(hours=2)


@dataclass(slots=True)
class WatchdogResult:
    """Outcome of evaluating the dead man's switch."""

    healthy: bool
    alert_needed: bool
    last_success_at: str | None
    last_error: str | None
    hours_since_success: float | None
    checked_at: str


def run_dead_mans_switch(
    *,
    trajectory_path: Path = _TRAJECTORY_PATH,
    now: datetime | None = None,
    threshold: timedelta = _SUCCESS_THRESHOLD,
    notifier: Any | None = None,
) -> WatchdogResult:
    """Alert when no successful marketing cycle completed within the threshold."""
    current_time = now or datetime.now(UTC)
    records = _read_cycle_records(trajectory_path)

    last_success = _latest_success(records)
    last_error = _latest_error(records)

    if last_success is None:
        hours_since = None
        alert_needed = bool(records)
    else:
        hours_since = round((current_time - last_success).total_seconds() / 3600, 3)
        alert_needed = (current_time - last_success) > threshold

    if alert_needed and notifier is not None:
        last_error_text = last_error or "unknown"
        notifier(
            f"Holus has not posted in 2 hours. Last error: {last_error_text}",
        )

    return WatchdogResult(
        healthy=not alert_needed,
        alert_needed=alert_needed,
        last_success_at=last_success.isoformat() if last_success else None,
        last_error=last_error,
        hours_since_success=hours_since,
        checked_at=current_time.isoformat(),
    )


def _read_cycle_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed watchdog trajectory line")
                continue
            if _is_cycle_record(payload):
                records.append(payload)
    return records


def _is_cycle_record(payload: dict[str, Any]) -> bool:
    if payload.get("task_type") == "cycle":
        return True
    return "cycle_id" in payload and "phase" in payload


def _latest_success(records: list[dict[str, Any]]) -> datetime | None:
    successes = [
        _parse_timestamp(record)
        for record in records
        if record.get("phase") == "done" or record.get("status") == "success"
    ]
    valid = [item for item in successes if item is not None]
    return max(valid) if valid else None


def _latest_error(records: list[dict[str, Any]]) -> str | None:
    for record in sorted(records, key=_sort_key, reverse=True):
        error = record.get("error")
        if isinstance(error, str) and error:
            return error
        health = record.get("health")
        if isinstance(health, dict):
            reason = health.get("reason")
            if isinstance(reason, str) and reason:
                return reason
    return None


def _parse_timestamp(record: dict[str, Any]) -> datetime | None:
    raw = record.get("timestamp") or record.get("cycle_id")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sort_key(record: dict[str, Any]) -> datetime:
    return _parse_timestamp(record) or datetime.min.replace(tzinfo=UTC)
