"""Tests for holus.core.watchdog — dead man's switch."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path  # noqa: TC003

from holus.core.watchdog import WatchdogResult, check_watchdog, consecutive_failure_check

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_entry(path: Path, entry: dict) -> None:  # type: ignore[type-arg]
    """Append a JSON line to path, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _done_entry(cycle_id: str, duration: float = 10.0, error: str | None = None) -> dict:  # type: ignore[type-arg]
    return {
        "cycle_id": cycle_id,
        "phase": "done",
        "duration_seconds": duration,
        "error": error,
    }


def _failed_entry(cycle_id: str, error: str = "some error", duration: float = 5.0) -> dict:  # type: ignore[type-arg]
    return {
        "cycle_id": cycle_id,
        "phase": "failed",
        "duration_seconds": duration,
        "error": error,
    }


def _transition_entry(cycle_id: str) -> dict:  # type: ignore[type-arg]
    """A transition entry (no 'phase' key) — should be ignored by watchdog."""
    return {
        "cycle_id": cycle_id,
        "event": "transition",
        "from_state": "starting",
        "to_state": "health_check",
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _recent_cycle_id(delta: timedelta = timedelta(minutes=10)) -> str:
    """Return a cycle_id (ISO timestamp) that is *delta* ago."""
    return (datetime.now(UTC) - delta).isoformat()


def _old_cycle_id(hours: float = 3.0) -> str:
    """Return a cycle_id that is *hours* ago."""
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# Healthy state
# ---------------------------------------------------------------------------


class TestWatchdogHealthy:
    def test_recent_done_no_alert(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_recent_cycle_id(timedelta(minutes=30))))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.alert is False

    def test_silence_hours_is_small(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_recent_cycle_id(timedelta(minutes=5))))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.silence_hours < 1.0

    def test_last_success_at_is_set(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        cycle_id = _recent_cycle_id(timedelta(minutes=10))
        _write_entry(traj, _done_entry(cycle_id, duration=10.0))

        result = check_watchdog(traj)

        assert result.last_success_at is not None
        assert isinstance(result.last_success_at, datetime)

    def test_last_error_is_none_when_no_failures(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_recent_cycle_id()))

        result = check_watchdog(traj)

        assert result.last_error is None

    def test_most_recent_done_used_when_multiple_entries(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        # Old success then new success — should see no alert
        _write_entry(traj, _done_entry(_old_cycle_id(5.0)))
        _write_entry(traj, _done_entry(_recent_cycle_id(timedelta(minutes=20))))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.alert is False

    def test_transition_entries_ignored(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        # Only transition entries + a done entry
        _write_entry(traj, _transition_entry("id-1"))
        _write_entry(traj, _done_entry(_recent_cycle_id(timedelta(minutes=5))))

        result = check_watchdog(traj)

        assert result.alert is False


# ---------------------------------------------------------------------------
# Alert state
# ---------------------------------------------------------------------------


class TestWatchdogAlert:
    def test_old_done_triggers_alert(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_old_cycle_id(3.0)))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.alert is True

    def test_silence_hours_reflects_actual_gap(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_old_cycle_id(3.0), duration=0.0))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.silence_hours > 2.9  # 3 hours ago

    def test_last_error_populated_from_recent_failure(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        # Old success, then recent failure
        _write_entry(traj, _done_entry(_old_cycle_id(5.0)))
        _write_entry(traj, _failed_entry(_old_cycle_id(3.0), error="LLM timeout"))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.alert is True
        assert result.last_error == "LLM timeout"

    def test_empty_trajectory_triggers_alert(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"

        result = check_watchdog(traj)

        assert result.alert is True
        assert result.silence_hours == float("inf")

    def test_missing_file_triggers_alert(self, tmp_path: Path) -> None:
        traj = tmp_path / "does_not_exist.jsonl"

        result = check_watchdog(traj)

        assert result.alert is True

    def test_all_failures_no_done_triggers_alert(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _failed_entry(_recent_cycle_id(timedelta(minutes=5)), error="error 1"))
        _write_entry(traj, _failed_entry(_recent_cycle_id(timedelta(minutes=3)), error="error 2"))

        result = check_watchdog(traj, max_silence_hours=2.0)

        assert result.alert is True
        assert result.last_success_at is None
        assert result.last_error is not None

    def test_silence_hours_inf_when_no_success(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _failed_entry(_recent_cycle_id()))

        result = check_watchdog(traj)

        assert result.silence_hours == float("inf")


# ---------------------------------------------------------------------------
# Returns correct type
# ---------------------------------------------------------------------------


class TestWatchdogReturnType:
    def test_returns_watchdog_result(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_recent_cycle_id()))

        result = check_watchdog(traj)

        assert isinstance(result, WatchdogResult)

    def test_watchdog_result_fields(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry(_recent_cycle_id()))

        result = check_watchdog(traj)

        assert isinstance(result.alert, bool)
        assert isinstance(result.silence_hours, float)


# ---------------------------------------------------------------------------
# consecutive_failure_check
# ---------------------------------------------------------------------------


class TestConsecutiveFailureCheck:
    def test_three_consecutive_failures_returns_true(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        for i in range(3):
            _write_entry(traj, _failed_entry(f"cycle-{i}"))

        assert consecutive_failure_check(traj, threshold=3) is True

    def test_two_failures_threshold_three_returns_false(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        for i in range(2):
            _write_entry(traj, _failed_entry(f"cycle-{i}"))

        assert consecutive_failure_check(traj, threshold=3) is False

    def test_success_in_last_n_returns_false(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _failed_entry("cycle-0"))
        _write_entry(traj, _failed_entry("cycle-1"))
        _write_entry(traj, _done_entry("cycle-2"))  # most recent is done

        assert consecutive_failure_check(traj, threshold=3) is False

    def test_success_then_two_failures_returns_false(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        _write_entry(traj, _done_entry("cycle-0"))
        _write_entry(traj, _failed_entry("cycle-1"))
        _write_entry(traj, _failed_entry("cycle-2"))

        # Last 3 include a success → False
        assert consecutive_failure_check(traj, threshold=3) is False

    def test_exactly_threshold_failures(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        for i in range(5):
            _write_entry(traj, _failed_entry(f"cycle-{i}"))

        assert consecutive_failure_check(traj, threshold=5) is True

    def test_empty_trajectory_returns_false(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"

        assert consecutive_failure_check(traj, threshold=3) is False

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        traj = tmp_path / "no_file.jsonl"

        assert consecutive_failure_check(traj, threshold=3) is False

    def test_transition_entries_not_counted(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        # Two failures + a transition (transition ignored) = only 2 summaries < threshold 3
        _write_entry(traj, _failed_entry("cycle-0"))
        _write_entry(traj, _failed_entry("cycle-1"))
        _write_entry(traj, _transition_entry("cycle-2"))

        assert consecutive_failure_check(traj, threshold=3) is False

    def test_default_threshold_is_three(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        for i in range(3):
            _write_entry(traj, _failed_entry(f"cycle-{i}"))

        assert consecutive_failure_check(traj) is True

    def test_more_than_threshold_entries_checks_last_n(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        # 2 old successes, then 3 failures
        _write_entry(traj, _done_entry("old-0"))
        _write_entry(traj, _done_entry("old-1"))
        for i in range(3):
            _write_entry(traj, _failed_entry(f"recent-{i}"))

        assert consecutive_failure_check(traj, threshold=3) is True


# ---------------------------------------------------------------------------
# WatchdogResult Pydantic model
# ---------------------------------------------------------------------------


class TestWatchdogResultModel:
    def test_is_pydantic_model(self) -> None:
        result = WatchdogResult(
            alert=False,
            last_success_at=None,
            last_error=None,
            silence_hours=0.5,
        )
        assert isinstance(result, WatchdogResult)

    def test_fields_accessible(self) -> None:
        now = datetime.now(UTC)
        result = WatchdogResult(
            alert=True,
            last_success_at=now,
            last_error="timeout",
            silence_hours=3.5,
        )
        assert result.alert is True
        assert result.last_success_at == now
        assert result.last_error == "timeout"
        assert result.silence_hours == 3.5
