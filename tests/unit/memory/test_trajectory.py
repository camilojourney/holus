"""Tests for holus.memory.trajectory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

if TYPE_CHECKING:
    from pathlib import Path


def test_append_creates_file(tmp_path: Path) -> None:
    """TrajectoryLogger.append creates the file if it doesn't exist."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    entry = TrajectoryEntry(
        agent_id="test-agent",
        task_type="test_task",
        task_summary="Test task summary",
        status="success",
    )
    tl.append(entry)

    assert path.exists()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1


def test_append_and_read_all(tmp_path: Path) -> None:
    """Entries can be appended and read back."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    for i in range(3):
        tl.append(
            TrajectoryEntry(
                agent_id=f"agent-{i}",
                task_type="build_cycle",
                task_summary=f"Task {i}",
                status="success",
            )
        )

    entries = tl.read_all()
    assert len(entries) == 3
    assert entries[0].agent_id == "agent-0"
    assert entries[2].agent_id == "agent-2"


def test_read_all_empty_file(tmp_path: Path) -> None:
    """read_all returns empty list when file doesn't exist."""
    path = tmp_path / "nonexistent.jsonl"
    tl = TrajectoryLogger(path)

    entries = tl.read_all()
    assert entries == []


def test_read_filtered_by_agent_id(tmp_path: Path) -> None:
    """read_filtered can filter by agent_id."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    tl.append(
        TrajectoryEntry(
            agent_id="marketing", task_type="cycle", task_summary="m1", status="success"
        )
    )
    tl.append(
        TrajectoryEntry(agent_id="builder", task_type="cycle", task_summary="b1", status="success")
    )
    tl.append(
        TrajectoryEntry(agent_id="marketing", task_type="cycle", task_summary="m2", status="error")
    )

    marketing = tl.read_filtered(agent_id="marketing")
    assert len(marketing) == 2
    assert all(e.agent_id == "marketing" for e in marketing)


def test_read_filtered_by_status(tmp_path: Path) -> None:
    """read_filtered can filter by status."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="success"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="success"))

    failures = tl.read_filtered(status="failure")
    assert len(failures) == 1


def test_read_filtered_with_limit(tmp_path: Path) -> None:
    """read_filtered respects the limit parameter."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    for i in range(10):
        tl.append(
            TrajectoryEntry(agent_id="a", task_type="t", task_summary=f"s{i}", status="success")
        )

    limited = tl.read_filtered(limit=3)
    assert len(limited) == 3


def test_failure_streak_counts_consecutive_failures(tmp_path: Path) -> None:
    """failure_streak counts consecutive recent failures."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="success"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="error"))

    streak = tl.failure_streak("a")
    assert streak == 3  # error + failure + failure (most recent first)


def test_failure_streak_broken_by_success(tmp_path: Path) -> None:
    """A success in the middle breaks the streak."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="success"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))

    streak = tl.failure_streak("a")
    assert streak == 1  # Only the most recent failure


def test_needs_optimization_threshold(tmp_path: Path) -> None:
    """needs_optimization triggers at the configured threshold."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    # 2 failures — below threshold
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    assert not tl.needs_optimization("a", threshold=3)

    # 3rd failure — at threshold
    tl.append(TrajectoryEntry(agent_id="a", task_type="t", task_summary="s", status="failure"))
    assert tl.needs_optimization("a", threshold=3)


def test_summary_stats(tmp_path: Path) -> None:
    """summary returns correct aggregate stats."""
    path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(path)

    tl.append(
        TrajectoryEntry(
            agent_id="a",
            task_type="t",
            task_summary="s",
            status="success",
            cost_usd=0.05,
            input_tokens=100,
            output_tokens=50,
        )
    )
    tl.append(
        TrajectoryEntry(
            agent_id="a",
            task_type="t",
            task_summary="s",
            status="failure",
            cost_usd=0.03,
            input_tokens=80,
            output_tokens=40,
        )
    )

    stats = tl.summary(agent_id="a")
    assert stats["total"] == 2
    assert stats["statuses"]["success"] == 1
    assert stats["statuses"]["failure"] == 1
    assert stats["total_cost_usd"] == 0.08
    assert stats["total_tokens"] == 270


def test_trajectory_entry_to_dict_roundtrip() -> None:
    """TrajectoryEntry can be serialized and deserialized."""
    entry = TrajectoryEntry(
        agent_id="test",
        task_type="build",
        task_summary="Test roundtrip",
        status="success",
        cost_usd=0.10,
        metadata={"key": "value"},
    )

    data = entry.to_dict()
    restored = TrajectoryEntry.from_dict(data)

    assert restored.agent_id == entry.agent_id
    assert restored.task_type == entry.task_type
    assert restored.status == entry.status
    assert restored.cost_usd == entry.cost_usd
    assert restored.metadata == {"key": "value"}
