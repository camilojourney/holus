"""Tests for holus.memory.knowledge_gaps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from holus.memory.knowledge_gaps import (
    KnowledgeGap,
    file_knowledge_gap,
    list_open_gaps,
    resolve_gap,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_file_knowledge_gap_creates_file(tmp_path: Path) -> None:
    """file_knowledge_gap creates a markdown request file."""
    path = file_knowledge_gap(
        filed_by="marketing-agent",
        what_i_need="LinkedIn optimal posting times by industry",
        why_i_need_it="Need to schedule posts at high-engagement times",
        priority="high",
        related_topic="platforms",
        requests_dir=tmp_path,
    )

    assert path.exists()
    assert path.suffix == ".md"
    content = path.read_text()
    assert "**Filed by:** marketing-agent" in content
    assert "**Priority:** high" in content
    assert "**Related topic:** platforms" in content
    assert "LinkedIn optimal posting times by industry" in content
    assert "Need to schedule posts at high-engagement times" in content
    assert "- [ ] Researched" in content
    assert "- [ ] Written to knowledge file" in content
    assert "- [ ] Request closed" in content


def test_file_knowledge_gap_default_priority(tmp_path: Path) -> None:
    """Default priority is medium."""
    path = file_knowledge_gap(
        filed_by="test-agent",
        what_i_need="Some info",
        why_i_need_it="Some reason",
        requests_dir=tmp_path,
    )
    content = path.read_text()
    assert "**Priority:** medium" in content


def test_file_knowledge_gap_creates_directory(tmp_path: Path) -> None:
    """Requests directory is created if it doesn't exist."""
    nested = tmp_path / "deep" / "nested" / "requests"
    path = file_knowledge_gap(
        filed_by="test-agent",
        what_i_need="Something",
        why_i_need_it="Because",
        requests_dir=nested,
    )
    assert path.exists()
    assert nested.exists()


def test_file_knowledge_gap_handles_duplicate_slugs(tmp_path: Path) -> None:
    """Duplicate slugs on the same day get a counter suffix."""
    path1 = file_knowledge_gap(
        filed_by="agent",
        what_i_need="Same topic",
        why_i_need_it="First request",
        requests_dir=tmp_path,
    )
    path2 = file_knowledge_gap(
        filed_by="agent",
        what_i_need="Same topic",
        why_i_need_it="Second request",
        requests_dir=tmp_path,
    )

    assert path1 != path2
    assert path1.exists()
    assert path2.exists()
    assert "Second request" in path2.read_text()


def test_list_open_gaps_empty_dir(tmp_path: Path) -> None:
    """list_open_gaps returns empty list when directory doesn't exist."""
    nonexistent = tmp_path / "nope"
    gaps = list_open_gaps(requests_dir=nonexistent)
    assert gaps == []


def test_list_open_gaps_returns_unresolved(tmp_path: Path) -> None:
    """list_open_gaps returns only unresolved gaps."""
    file_knowledge_gap(
        filed_by="agent-a",
        what_i_need="Topic A",
        why_i_need_it="Reason A",
        priority="high",
        requests_dir=tmp_path,
    )
    path_b = file_knowledge_gap(
        filed_by="agent-b",
        what_i_need="Topic B",
        why_i_need_it="Reason B",
        priority="low",
        requests_dir=tmp_path,
    )

    # Resolve one gap
    resolve_gap(path_b)

    gaps = list_open_gaps(requests_dir=tmp_path)
    assert len(gaps) == 1
    assert gaps[0].filed_by == "agent-a"


def test_list_open_gaps_sorted_by_priority(tmp_path: Path) -> None:
    """Gaps are sorted by priority (critical first)."""
    file_knowledge_gap(
        filed_by="a",
        what_i_need="Low item",
        why_i_need_it="r",
        priority="low",
        requests_dir=tmp_path,
    )
    file_knowledge_gap(
        filed_by="b",
        what_i_need="Critical item",
        why_i_need_it="r",
        priority="critical",
        requests_dir=tmp_path,
    )
    file_knowledge_gap(
        filed_by="c",
        what_i_need="High item",
        why_i_need_it="r",
        priority="high",
        requests_dir=tmp_path,
    )

    gaps = list_open_gaps(requests_dir=tmp_path)
    assert len(gaps) == 3
    assert gaps[0].priority == "critical"
    assert gaps[1].priority == "high"
    assert gaps[2].priority == "low"


def test_list_open_gaps_filter_by_priority(tmp_path: Path) -> None:
    """list_open_gaps can filter by priority level."""
    file_knowledge_gap(
        filed_by="a",
        what_i_need="High one",
        why_i_need_it="r",
        priority="high",
        requests_dir=tmp_path,
    )
    file_knowledge_gap(
        filed_by="b",
        what_i_need="Low one",
        why_i_need_it="r",
        priority="low",
        requests_dir=tmp_path,
    )

    high_gaps = list_open_gaps(requests_dir=tmp_path, priority="high")
    assert len(high_gaps) == 1
    assert high_gaps[0].priority == "high"


def test_list_open_gaps_skips_readme(tmp_path: Path) -> None:
    """README.md in the requests dir is not parsed as a gap."""
    (tmp_path / "README.md").write_text("# Knowledge Gap Requests\n")
    file_knowledge_gap(
        filed_by="agent",
        what_i_need="Real gap",
        why_i_need_it="r",
        requests_dir=tmp_path,
    )

    gaps = list_open_gaps(requests_dir=tmp_path)
    assert len(gaps) == 1
    assert gaps[0].what_i_need == "Real gap"


def test_resolve_gap_marks_all_checkboxes(tmp_path: Path) -> None:
    """resolve_gap checks all three status checkboxes."""
    path = file_knowledge_gap(
        filed_by="agent",
        what_i_need="Something",
        why_i_need_it="Reason",
        requests_dir=tmp_path,
    )

    assert resolve_gap(path) is True

    content = path.read_text()
    assert "- [x] Researched" in content
    assert "- [x] Written to knowledge file" in content
    assert "- [x] Request closed" in content

    # Verify it's now excluded from open gaps
    gaps = list_open_gaps(requests_dir=tmp_path)
    assert len(gaps) == 0


def test_resolve_gap_nonexistent_file(tmp_path: Path) -> None:
    """resolve_gap returns False for nonexistent files."""
    assert resolve_gap(tmp_path / "nope.md") is False


def test_knowledge_gap_dataclass_fields(tmp_path: Path) -> None:
    """KnowledgeGap has all expected fields parsed correctly."""
    path = file_knowledge_gap(
        filed_by="marketing-agent",
        what_i_need="Best hashtags for AI art",
        why_i_need_it="Need to optimize Instagram reach",
        priority="high",
        related_topic="platforms",
        requests_dir=tmp_path,
    )

    gaps = list_open_gaps(requests_dir=tmp_path)
    assert len(gaps) == 1

    gap = gaps[0]
    assert isinstance(gap, KnowledgeGap)
    assert gap.path == path
    assert gap.filed_by == "marketing-agent"
    assert gap.priority == "high"
    assert gap.related_topic == "platforms"
    assert gap.what_i_need == "Best hashtags for AI art"
    assert gap.why_i_need_it == "Need to optimize Instagram reach"
    assert gap.is_resolved is False


def test_file_knowledge_gap_slugifies_long_names(tmp_path: Path) -> None:
    """Long what_i_need strings are truncated in the filename slug."""
    long_desc = "A" * 200
    path = file_knowledge_gap(
        filed_by="agent",
        what_i_need=long_desc,
        why_i_need_it="r",
        requests_dir=tmp_path,
    )
    # Slug is capped at 50 chars + date prefix + .md suffix
    assert len(path.stem) <= 61  # date(10) + dash(1) + slug(50)
    assert path.exists()
