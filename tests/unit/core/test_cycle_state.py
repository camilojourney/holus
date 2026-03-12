"""Tests for holus.core.cycle_state — CycleState machine + trajectory contract."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from holus.core.cycle_state import (
    CycleContext,
    CycleState,
    HealthResult,
    _append_jsonl,
    write_trajectory_entry,
)

# ---------------------------------------------------------------------------
# CycleState enum
# ---------------------------------------------------------------------------


class TestCycleStateEnum:
    """CycleState must define all 12 states."""

    def test_all_twelve_states_defined(self) -> None:
        expected = {
            "starting",
            "health_check",
            "loading_state",
            "observing",
            "reasoning",
            "creating",
            "quality_check",
            "posting",
            "improving",
            "saving_state",
            "done",
            "failed",
        }
        actual = {s.value for s in CycleState}
        assert actual == expected

    def test_state_is_str(self) -> None:
        assert isinstance(CycleState.STARTING, str)
        assert CycleState.DONE == "done"
        assert CycleState.FAILED == "failed"


# ---------------------------------------------------------------------------
# HealthResult
# ---------------------------------------------------------------------------


class TestHealthResult:
    def test_fields(self) -> None:
        hr = HealthResult(
            blocking_ok=True,
            available_silos=["social_media", "pilaster"],
            warnings=["Genpeli unreachable"],
        )
        assert hr.blocking_ok is True
        assert "social_media" in hr.available_silos
        assert len(hr.warnings) == 1

    def test_blocking_false(self) -> None:
        hr = HealthResult(blocking_ok=False, available_silos=[], warnings=["kill switch active"])
        assert hr.blocking_ok is False
        assert hr.available_silos == []


# ---------------------------------------------------------------------------
# CycleContext
# ---------------------------------------------------------------------------


class TestCycleContextFactory:
    def test_new_returns_starting_state(self) -> None:
        ctx = CycleContext.new()
        assert ctx.current_state == CycleState.STARTING

    def test_new_generates_iso_cycle_id(self) -> None:
        ctx = CycleContext.new()
        # Must be parseable as a datetime
        parsed = datetime.fromisoformat(ctx.cycle_id)
        assert parsed.tzinfo is not None  # timezone-aware

    def test_new_defaults(self) -> None:
        ctx = CycleContext.new()
        assert ctx.health_result is None
        assert ctx.content_created == 0
        assert ctx.content_posted == 0
        assert ctx.content_failed == 0
        assert ctx.quality_scores == []
        assert ctx.capability_gaps == []
        assert ctx.error is None
        assert ctx.duration_seconds is None

    def test_custom_trajectory_path(self, tmp_path: Path) -> None:
        traj = tmp_path / "custom.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        assert ctx.trajectory_path == traj


class TestCycleContextTransition:
    def test_transition_updates_current_state(self, tmp_path: Path) -> None:
        ctx = CycleContext.new(trajectory_path=tmp_path / "traj.jsonl")
        ctx.transition(CycleState.HEALTH_CHECK)
        assert ctx.current_state == CycleState.HEALTH_CHECK

    def test_transition_appends_to_trajectory(self, tmp_path: Path) -> None:
        traj = tmp_path / "traj.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.HEALTH_CHECK)
        ctx.transition(CycleState.OBSERVING)

        lines = traj.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_transition_log_has_correct_keys(self, tmp_path: Path) -> None:
        traj = tmp_path / "traj.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.REASONING)

        entry = json.loads(traj.read_text().strip())
        assert entry["cycle_id"] == ctx.cycle_id
        assert entry["event"] == "transition"
        assert entry["from_state"] == "starting"
        assert entry["to_state"] == "reasoning"
        assert "timestamp" in entry

    def test_multiple_transitions_sequential(self, tmp_path: Path) -> None:
        traj = tmp_path / "traj.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)

        states = [
            CycleState.HEALTH_CHECK,
            CycleState.LOADING_STATE,
            CycleState.OBSERVING,
            CycleState.REASONING,
            CycleState.CREATING,
            CycleState.DONE,
        ]
        for state in states:
            ctx.transition(state)

        assert ctx.current_state == CycleState.DONE
        lines = traj.read_text().strip().splitlines()
        assert len(lines) == len(states)

    def test_transition_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested" / "traj.jsonl"
        ctx = CycleContext.new(trajectory_path=nested)
        ctx.transition(CycleState.HEALTH_CHECK)
        assert nested.exists()

    def test_transition_to_failed(self, tmp_path: Path) -> None:
        traj = tmp_path / "traj.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.error = "LLM timeout"
        ctx.transition(CycleState.FAILED)
        assert ctx.current_state == CycleState.FAILED


class TestCycleContextFinish:
    def test_finish_sets_duration(self, tmp_path: Path) -> None:
        ctx = CycleContext.new(trajectory_path=tmp_path / "traj.jsonl")
        ctx.finish()
        assert ctx.duration_seconds is not None
        assert ctx.duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# write_trajectory_entry
# ---------------------------------------------------------------------------


class TestWriteTrajectoryEntry:
    def test_writes_json_line(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)

        # One transition line + one summary line
        lines = traj.read_text().strip().splitlines()
        # Find the summary entry (has "phase" key)
        summaries = [json.loads(line) for line in lines if "phase" in json.loads(line)]
        assert len(summaries) == 1

    def test_summary_has_required_keys(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)

        lines = traj.read_text().strip().splitlines()
        entry = next(json.loads(line) for line in lines if "phase" in json.loads(line))

        required_keys = {
            "cycle_id",
            "phase",
            "health",
            "content_created",
            "content_posted",
            "content_failed",
            "quality_scores",
            "capability_gaps",
            "duration_seconds",
            "error",
        }
        assert required_keys.issubset(entry.keys())

    def test_summary_phase_matches_state(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.FAILED)
        ctx.error = "timeout"
        write_trajectory_entry(ctx)

        lines = traj.read_text().strip().splitlines()
        entry = next(json.loads(line) for line in lines if "phase" in json.loads(line))
        assert entry["phase"] == "failed"
        assert entry["error"] == "timeout"

    def test_summary_with_health_result(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.health_result = HealthResult(
            blocking_ok=True,
            available_silos=["social_media"],
            warnings=["Genpeli down"],
        )
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)

        lines = traj.read_text().strip().splitlines()
        entry = next(json.loads(line) for line in lines if "phase" in json.loads(line))
        assert entry["health"]["blocking_ok"] is True
        assert entry["health"]["available_silos"] == ["social_media"]
        assert entry["health"]["warnings"] == ["Genpeli down"]

    def test_summary_null_health_when_not_set(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.FAILED)
        write_trajectory_entry(ctx)

        lines = traj.read_text().strip().splitlines()
        entry = next(json.loads(line) for line in lines if "phase" in json.loads(line))
        assert entry["health"] is None

    def test_summary_content_counts(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.content_created = 3
        ctx.content_posted = 2
        ctx.content_failed = 1
        ctx.quality_scores = [0.8, 0.9]
        ctx.capability_gaps = ["genpeli unavailable"]
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)

        lines = traj.read_text().strip().splitlines()
        entry = next(json.loads(line) for line in lines if "phase" in json.loads(line))
        assert entry["content_created"] == 3
        assert entry["content_posted"] == 2
        assert entry["content_failed"] == 1
        assert entry["quality_scores"] == [0.8, 0.9]
        assert entry["capability_gaps"] == ["genpeli unavailable"]

    def test_write_sets_duration_if_missing(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        ctx = CycleContext.new(trajectory_path=traj)
        assert ctx.duration_seconds is None
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)
        assert ctx.duration_seconds is not None

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        traj = tmp_path / "memory" / "trajectory.jsonl"
        assert not traj.parent.exists()
        ctx = CycleContext.new(trajectory_path=traj)
        ctx.transition(CycleState.DONE)
        write_trajectory_entry(ctx)
        assert traj.exists()

    def test_appends_multiple_entries(self, tmp_path: Path) -> None:
        traj = tmp_path / "trajectory.jsonl"
        for _ in range(3):
            ctx = CycleContext.new(trajectory_path=traj)
            ctx.transition(CycleState.DONE)
            write_trajectory_entry(ctx)

        all_lines = traj.read_text().strip().splitlines()
        summaries = [json.loads(line) for line in all_lines if "phase" in json.loads(line)]
        assert len(summaries) == 3


# ---------------------------------------------------------------------------
# _append_jsonl (internal helper — tested for robustness)
# ---------------------------------------------------------------------------


class TestAppendJsonl:
    def test_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonl"
        _append_jsonl(path, {"key": "value"})
        assert path.exists()
        data = json.loads(path.read_text().strip())
        assert data["key"] == "value"

    def test_appends_multiple_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonl"
        _append_jsonl(path, {"n": 1})
        _append_jsonl(path, {"n": 2})
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["n"] == 2

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "c.jsonl"
        _append_jsonl(path, {"x": 1})
        assert path.exists()

    def test_does_not_raise_on_write_failure(self) -> None:
        # Write to a path that can't be created — should log, not raise
        bad_path = Path("/nonexistent_root_dir/a/b/c.jsonl")
        # Must not raise
        _append_jsonl(bad_path, {"key": "value"})
