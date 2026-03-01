"""Tests for holus.memory.knowledge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from holus.memory.knowledge import (
    KnowledgeFile,
    load_knowledge_files,
    validate_knowledge_file,
)

if TYPE_CHECKING:
    from pathlib import Path

VALID_KNOWLEDGE_FILE = """\
# Knowledge: Test Topic

**Last updated:** 2026-03-01
**Updated by:** human
**Confidence:** high
**Affects:** marketing agent decisions
**Research cadence:** weekly

---

## Section One

Some content here.
"""

VALID_KNOWLEDGE_FILE_WITH_NOTES = """\
# Knowledge: Audience Profiles

**Last updated:** 2026-02-26
**Updated by:** human + research agent
**Confidence:** medium (needs validation from analytics)
**Affects:** content tone, platform selection, content type decisions
**Research cadence:** monthly

---

## Primary Audiences

Details here.
"""


def _write_knowledge_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_validate_valid_file(tmp_path: Path) -> None:
    """A well-formed knowledge file passes validation."""
    path = _write_knowledge_file(tmp_path, "test.md", VALID_KNOWLEDGE_FILE)
    kf = validate_knowledge_file(path)

    assert kf.is_valid
    assert kf.errors == ()
    assert kf.title == "Knowledge: Test Topic"
    assert kf.last_updated == "2026-03-01"
    assert kf.updated_by == "human"
    assert kf.confidence == "high"
    assert kf.affects == "marketing agent decisions"
    assert kf.research_cadence == "weekly"


def test_validate_confidence_with_parenthetical_notes(tmp_path: Path) -> None:
    """Confidence like 'medium (needs validation)' is valid."""
    path = _write_knowledge_file(tmp_path, "test.md", VALID_KNOWLEDGE_FILE_WITH_NOTES)
    kf = validate_knowledge_file(path)

    assert kf.is_valid
    assert kf.confidence == "medium (needs validation from analytics)"


def test_validate_missing_header(tmp_path: Path) -> None:
    """Missing a required header produces a validation error."""
    content = """\
# Knowledge: Incomplete

**Last updated:** 2026-03-01
**Updated by:** human
**Affects:** something

Some content.
"""
    path = _write_knowledge_file(tmp_path, "incomplete.md", content)
    kf = validate_knowledge_file(path)

    assert not kf.is_valid
    assert any("Confidence" in e for e in kf.errors)
    assert any("Research cadence" in e for e in kf.errors)


def test_validate_missing_title(tmp_path: Path) -> None:
    """Missing H1 title produces a validation error."""
    content = """\
**Last updated:** 2026-03-01
**Updated by:** human
**Confidence:** high
**Affects:** something
**Research cadence:** weekly
"""
    path = _write_knowledge_file(tmp_path, "no-title.md", content)
    kf = validate_knowledge_file(path)

    assert not kf.is_valid
    assert any("title" in e.lower() for e in kf.errors)


def test_validate_invalid_confidence_level(tmp_path: Path) -> None:
    """Invalid confidence level produces a validation error."""
    content = """\
# Knowledge: Bad Confidence

**Last updated:** 2026-03-01
**Updated by:** human
**Confidence:** very-sure
**Affects:** something
**Research cadence:** weekly
"""
    path = _write_knowledge_file(tmp_path, "bad-conf.md", content)
    kf = validate_knowledge_file(path)

    assert not kf.is_valid
    assert any("confidence level" in e.lower() for e in kf.errors)


def test_validate_nonexistent_file(tmp_path: Path) -> None:
    """Nonexistent file returns a KnowledgeFile with error."""
    path = tmp_path / "ghost.md"
    kf = validate_knowledge_file(path)

    assert not kf.is_valid
    assert any("Cannot read" in e for e in kf.errors)


def test_load_knowledge_files_empty_dir(tmp_path: Path) -> None:
    """load_knowledge_files returns empty list for nonexistent directory."""
    nonexistent = tmp_path / "nope"
    files = load_knowledge_files(knowledge_dir=nonexistent)
    assert files == []


def test_load_knowledge_files_loads_all(tmp_path: Path) -> None:
    """load_knowledge_files loads and validates all .md files."""
    _write_knowledge_file(tmp_path, "topic-a.md", VALID_KNOWLEDGE_FILE)
    _write_knowledge_file(
        tmp_path,
        "topic-b.md",
        VALID_KNOWLEDGE_FILE.replace("Test Topic", "Another Topic"),
    )

    files = load_knowledge_files(knowledge_dir=tmp_path)
    assert len(files) == 2
    assert all(isinstance(f, KnowledgeFile) for f in files)
    assert all(f.is_valid for f in files)


def test_load_knowledge_files_skips_readme(tmp_path: Path) -> None:
    """README.md in the knowledge directory is not loaded."""
    (tmp_path / "README.md").write_text("# Knowledge Index\n")
    _write_knowledge_file(tmp_path, "real.md", VALID_KNOWLEDGE_FILE)

    files = load_knowledge_files(knowledge_dir=tmp_path)
    assert len(files) == 1


def test_load_knowledge_files_includes_invalid_by_default(tmp_path: Path) -> None:
    """Invalid files are included when skip_invalid=True (default)."""
    _write_knowledge_file(tmp_path, "good.md", VALID_KNOWLEDGE_FILE)
    _write_knowledge_file(tmp_path, "bad.md", "No headers at all.\n")

    files = load_knowledge_files(knowledge_dir=tmp_path)
    assert len(files) == 2
    valid_count = sum(1 for f in files if f.is_valid)
    assert valid_count == 1


def test_load_knowledge_files_raises_on_invalid(tmp_path: Path) -> None:
    """skip_invalid=False raises ValueError on invalid files."""
    _write_knowledge_file(tmp_path, "bad.md", "No headers.\n")

    try:
        load_knowledge_files(knowledge_dir=tmp_path, skip_invalid=False)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_knowledge_file_content_preserved(tmp_path: Path) -> None:
    """The full file content is available on KnowledgeFile.content."""
    path = _write_knowledge_file(tmp_path, "test.md", VALID_KNOWLEDGE_FILE)
    kf = validate_knowledge_file(path)

    assert "Section One" in kf.content
    assert "Some content here." in kf.content


def test_load_knowledge_files_sorted_by_filename(tmp_path: Path) -> None:
    """Files are returned sorted by filename (alphabetical)."""
    _write_knowledge_file(
        tmp_path,
        "z-topic.md",
        VALID_KNOWLEDGE_FILE.replace("Test Topic", "Z Topic"),
    )
    _write_knowledge_file(
        tmp_path,
        "a-topic.md",
        VALID_KNOWLEDGE_FILE.replace("Test Topic", "A Topic"),
    )

    files = load_knowledge_files(knowledge_dir=tmp_path)
    assert files[0].title == "Knowledge: A Topic"
    assert files[1].title == "Knowledge: Z Topic"
