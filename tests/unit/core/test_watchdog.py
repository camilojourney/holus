"""Tests for holus.core.watchdog."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from holus.core.watchdog import run_dead_mans_switch


def test_watchdog_stays_healthy_with_recent_success(tmp_path) -> None:
    """A recent successful cycle should not alert."""
    trajectory = tmp_path / "trajectory.jsonl"
    trajectory.write_text(
        json.dumps(
            {
                "timestamp": "2026-03-12T09:30:00+00:00",
                "task_type": "cycle",
                "cycle_id": "2026-03-12T09:30:00Z",
                "phase": "done",
                "status": "success",
                "error": None,
            }
        )
        + "\n"
    )

    notifier = MagicMock()
    result = run_dead_mans_switch(
        trajectory_path=trajectory,
        now=datetime(2026, 3, 12, 10, 45, tzinfo=UTC),
        notifier=notifier,
    )

    assert result.healthy is True
    assert result.alert_needed is False
    notifier.assert_not_called()


def test_watchdog_alerts_after_two_hours_without_success(tmp_path) -> None:
    """Stale or failed-only cycles should trigger the dead man's switch."""
    trajectory = tmp_path / "trajectory.jsonl"
    trajectory.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-03-12T07:00:00+00:00",
                        "task_type": "cycle",
                        "cycle_id": "2026-03-12T07:00:00Z",
                        "phase": "done",
                        "status": "success",
                        "error": None,
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-03-12T09:30:00+00:00",
                        "task_type": "cycle",
                        "cycle_id": "2026-03-12T09:30:00Z",
                        "phase": "creating",
                        "status": "failure",
                        "error": "ConnectionError: http://localhost:8000",
                    }
                ),
            ]
        )
        + "\n"
    )

    notifier = MagicMock()
    result = run_dead_mans_switch(
        trajectory_path=trajectory,
        now=datetime(2026, 3, 12, 10, 15, tzinfo=UTC),
        notifier=notifier,
    )

    assert result.healthy is False
    assert result.alert_needed is True
    assert result.last_error == "ConnectionError: http://localhost:8000"
    notifier.assert_called_once()
