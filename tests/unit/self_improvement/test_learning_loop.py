"""Tests for holus.self_improvement.learning_loop."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger
from holus.self_improvement.learning_loop import (
    Insight,
    LearningReport,
    WeeklyLearningLoop,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    *,
    agent_id: str = "marketing-agent",
    task_type: str = "content_creation",
    status: str = "success",
    product: str = "pilaster",
    content_type: str = "tutorial",
    platform: str = "linkedin",
    minutes_ago: int = 0,
) -> TrajectoryEntry:
    """Create a trajectory entry with configurable metadata."""
    ts = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    return TrajectoryEntry(
        timestamp=ts,
        agent_id=agent_id,
        task_type=task_type,
        task_summary=f"{content_type} about {product} for {platform}",
        status=status,
        metadata={
            "product": product,
            "content_type": content_type,
            "platform": platform,
        },
    )


def _setup_loop(
    tmp_path: Path,
    entries: list[TrajectoryEntry],
    *,
    min_data_points: int = 5,
    memory_content: str | None = None,
) -> WeeklyLearningLoop:
    """Create a WeeklyLearningLoop with pre-populated trajectory data."""
    traj_path = tmp_path / "trajectory.jsonl"
    tl = TrajectoryLogger(traj_path)
    for entry in entries:
        tl.append(entry)

    memory_path = tmp_path / "MEMORY.md"
    if memory_content is None:
        memory_content = (
            "# Holus System Memory\n\n"
            "## Content Strategy (What We've Learned)\n\n"
            "_No data yet._\n\n"
            "---\n\n"
            "## Analytics Source\n\n"
            "All analytics data lives in social-media-automatization.\n"
        )
    memory_path.write_text(memory_content)

    knowledge_dir = tmp_path / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True)
    archive_dir = tmp_path / "knowledge" / "archive"

    return WeeklyLearningLoop(
        trajectory_path=traj_path,
        memory_path=memory_path,
        knowledge_dir=knowledge_dir,
        archive_dir=archive_dir,
        lookback_days=7,
        min_data_points=min_data_points,
    )


# ---------------------------------------------------------------------------
# Tests: Skipping on insufficient data
# ---------------------------------------------------------------------------


def test_skips_when_not_enough_data(tmp_path: Path) -> None:
    """Learning loop skips when trajectory has fewer than min_data_points."""
    entries = [_make_entry() for _ in range(3)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    report = loop.run()

    assert report.skipped_reason is not None
    assert "Not enough data" in report.skipped_reason
    assert report.trajectory_entries_analyzed == 3
    assert report.insights == []
    assert not report.memory_updated


def test_skips_when_no_trajectory(tmp_path: Path) -> None:
    """Learning loop skips when trajectory is empty."""
    loop = _setup_loop(tmp_path, [], min_data_points=5)

    report = loop.run()

    assert report.skipped_reason is not None
    assert report.trajectory_entries_analyzed == 0


def test_skips_old_entries_outside_lookback(tmp_path: Path) -> None:
    """Entries older than lookback_days are excluded."""
    old_entries = [
        _make_entry(minutes_ago=60 * 24 * 10)  # 10 days ago
        for _ in range(10)
    ]
    loop = _setup_loop(tmp_path, old_entries, min_data_points=5)

    report = loop.run()

    assert report.skipped_reason is not None
    assert report.trajectory_entries_analyzed == 0


# ---------------------------------------------------------------------------
# Tests: Pattern aggregation
# ---------------------------------------------------------------------------


def test_aggregate_patterns(tmp_path: Path) -> None:
    """Entries are grouped by product x content_type x platform."""
    entries = [
        _make_entry(product="pilaster", content_type="tutorial", platform="linkedin"),
        _make_entry(product="pilaster", content_type="tutorial", platform="linkedin"),
        _make_entry(product="genpeli", content_type="demo", platform="twitter"),
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=1)

    patterns = loop._aggregate_patterns(entries)

    assert "pilaster_tutorial_linkedin" in patterns
    assert patterns["pilaster_tutorial_linkedin"]["count"] == 2
    assert "genpeli_demo_twitter" in patterns
    assert patterns["genpeli_demo_twitter"]["count"] == 1


# ---------------------------------------------------------------------------
# Tests: Insight extraction
# ---------------------------------------------------------------------------


def test_extracts_most_active_content_type(tmp_path: Path) -> None:
    """Identifies the most active content type."""
    entries = [
        _make_entry(content_type="tutorial"),
        _make_entry(content_type="tutorial"),
        _make_entry(content_type="tutorial"),
        _make_entry(content_type="demo"),
        _make_entry(content_type="demo"),
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=1)
    patterns = loop._aggregate_patterns(entries)

    insights = loop._extract_insights(patterns, entries)

    type_insight = next(i for i in insights if "Most active content type" in i.pattern)
    assert "tutorial" in type_insight.pattern
    assert type_insight.source == "trajectory"


def test_extracts_success_rate(tmp_path: Path) -> None:
    """Calculates overall success rate."""
    entries = [
        _make_entry(status="success"),
        _make_entry(status="success"),
        _make_entry(status="success"),
        _make_entry(status="failure"),
        _make_entry(status="error"),
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=1)
    patterns = loop._aggregate_patterns(entries)

    insights = loop._extract_insights(patterns, entries)

    rate_insight = next(
        i for i in insights if "success rate" in i.pattern and "Overall" in i.pattern
    )
    assert "60%" in rate_insight.pattern
    assert rate_insight.sample_size == 5


def test_extracts_per_product_breakdown(tmp_path: Path) -> None:
    """Generates per-product insights when count >= 3."""
    entries = [
        _make_entry(product="pilaster"),
        _make_entry(product="pilaster"),
        _make_entry(product="pilaster"),
        _make_entry(product="genpeli"),  # only 1 — should not appear
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=1)
    patterns = loop._aggregate_patterns(entries)

    insights = loop._extract_insights(patterns, entries)

    product_insights = [i for i in insights if i.pattern.startswith("pilaster:")]
    assert len(product_insights) == 1
    assert "3 pieces" in product_insights[0].pattern

    # genpeli should NOT appear (only 1 entry)
    genpeli_insights = [i for i in insights if i.pattern.startswith("genpeli:")]
    assert len(genpeli_insights) == 0


def test_confidence_preliminary_for_small_samples(tmp_path: Path) -> None:
    """Confidence is preliminary when sample size < 20."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)
    patterns = loop._aggregate_patterns(entries)

    insights = loop._extract_insights(patterns, entries)

    for insight in insights:
        assert insight.confidence == "preliminary"


# ---------------------------------------------------------------------------
# Tests: MEMORY.md update
# ---------------------------------------------------------------------------


def test_updates_memory_md(tmp_path: Path) -> None:
    """Learning loop appends insights to MEMORY.md without overwriting."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    report = loop.run()

    assert report.memory_updated
    memory_text = loop.memory_path.read_text()
    assert "Learning Loop" in memory_text
    assert "Auto-generated" in memory_text
    # Original content preserved
    assert "Holus System Memory" in memory_text
    assert "Analytics Source" in memory_text


def test_memory_preserves_existing_content(tmp_path: Path) -> None:
    """Existing MEMORY.md sections are not overwritten."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    original = loop.memory_path.read_text()
    loop.run()
    updated = loop.memory_path.read_text()

    # Original content should still be there
    assert "Content Strategy" in updated
    assert "Analytics Source" in updated
    # New content should be added
    assert "Learning Loop" in updated
    assert len(updated) > len(original)


# ---------------------------------------------------------------------------
# Tests: performance-patterns.md
# ---------------------------------------------------------------------------


def test_creates_performance_patterns(tmp_path: Path) -> None:
    """Learning loop creates performance-patterns.md."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    report = loop.run()

    assert "performance-patterns.md" in report.knowledge_files_updated
    pp_path = loop.knowledge_dir / "performance-patterns.md"
    assert pp_path.exists()
    content = pp_path.read_text()
    assert "Knowledge: Performance Patterns" in content
    assert "**Last updated:**" in content
    assert "**Updated by:** learning-loop" in content
    assert "**Confidence:**" in content
    assert "**Research cadence:** weekly" in content


def test_performance_patterns_has_breakdown_table(tmp_path: Path) -> None:
    """Performance patterns file includes product x type x platform table."""
    entries = [
        _make_entry(product="pilaster", content_type="tutorial", platform="linkedin"),
        _make_entry(product="pilaster", content_type="demo", platform="twitter"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin"),
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)
    loop.run()

    pp_path = loop.knowledge_dir / "performance-patterns.md"
    content = pp_path.read_text()
    assert "Content Type x Platform Breakdown" in content
    assert "pilaster" in content
    assert "genpeli" in content


def test_archives_existing_performance_patterns(tmp_path: Path) -> None:
    """Existing performance-patterns.md is archived before update."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    # Create a pre-existing file with enough content to trigger archival
    pp_path = loop.knowledge_dir / "performance-patterns.md"
    pp_path.write_text("x" * 300)

    loop.run()

    # Archive should exist
    archive_files = list(loop.archive_dir.glob("performance-patterns-*.md"))
    assert len(archive_files) == 1


# ---------------------------------------------------------------------------
# Tests: Trajectory logging of the cycle
# ---------------------------------------------------------------------------


def test_logs_cycle_to_trajectory(tmp_path: Path) -> None:
    """The learning cycle itself is logged to trajectory."""
    entries = [_make_entry() for _ in range(6)]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    loop.run()

    all_entries = loop.trajectory.read_all()
    learning_entries = [e for e in all_entries if e.agent_id == "learning-loop"]
    assert len(learning_entries) == 1
    assert learning_entries[0].task_type == "weekly_learning"
    assert learning_entries[0].status == "success"


def test_logs_skipped_cycle_to_trajectory(tmp_path: Path) -> None:
    """Even skipped cycles are logged."""
    loop = _setup_loop(tmp_path, [], min_data_points=5)

    loop.run()

    all_entries = loop.trajectory.read_all()
    learning_entries = [e for e in all_entries if e.agent_id == "learning-loop"]
    assert len(learning_entries) == 1
    assert learning_entries[0].status == "partial"
    assert "Skipped" in learning_entries[0].task_summary


# ---------------------------------------------------------------------------
# Tests: Full run end-to-end
# ---------------------------------------------------------------------------


def test_full_run_produces_complete_report(tmp_path: Path) -> None:
    """Full end-to-end run produces all expected outputs."""
    entries = [
        _make_entry(product="pilaster", content_type="tutorial", platform="linkedin"),
        _make_entry(product="pilaster", content_type="tutorial", platform="linkedin"),
        _make_entry(product="pilaster", content_type="demo", platform="twitter"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin"),
        _make_entry(product="genpeli", content_type="demo", platform="linkedin", status="failure"),
    ]
    loop = _setup_loop(tmp_path, entries, min_data_points=5)

    report = loop.run()

    assert report.skipped_reason is None
    assert report.trajectory_entries_analyzed == 6
    assert len(report.insights) > 0
    assert report.memory_updated
    assert "performance-patterns.md" in report.knowledge_files_updated

    # MEMORY.md was updated
    memory = loop.memory_path.read_text()
    assert "Learning Loop" in memory

    # performance-patterns.md was created
    pp = (loop.knowledge_dir / "performance-patterns.md").read_text()
    assert "Performance Patterns" in pp

    # Trajectory has the learning-loop entry
    all_entries = loop.trajectory.read_all()
    assert any(e.agent_id == "learning-loop" for e in all_entries)


# ---------------------------------------------------------------------------
# Tests: LearningReport and Insight dataclasses
# ---------------------------------------------------------------------------


def test_learning_report_defaults() -> None:
    """LearningReport has sensible defaults."""
    report = LearningReport()
    assert report.trajectory_entries_analyzed == 0
    assert report.insights == []
    assert not report.memory_updated
    assert report.knowledge_files_updated == []
    assert report.skipped_reason is None


def test_insight_dataclass() -> None:
    """Insight dataclass stores all fields."""
    insight = Insight(
        pattern="tutorials outperform demos 2:1",
        confidence="medium",
        sample_size=42,
        source="trajectory",
    )
    assert insight.pattern == "tutorials outperform demos 2:1"
    assert insight.confidence == "medium"
    assert insight.sample_size == 42
    assert insight.source == "trajectory"
