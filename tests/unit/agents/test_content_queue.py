"""Tests for content_queue.py — enqueue, list, status transitions, YAML persistence.

Covers:
  - QueuedContent model — defaults, field validation
  - enqueue() — saves YAML file, returns path, creates directory
  - list_pending() — filters by status, handles empty dir, skips bad files
  - list_approved() — filters approved only
  - approve() — status transition pending_review → approved
  - reject() — status transition pending_review → rejected, stores reason
  - mark_published() — status transition approved → published, stores post_id
  - Edge cases — missing dir, missing file (FileNotFoundError), duplicate IDs
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import yaml

from holus.agents.marketing.content_queue import (
    QueuedContent,
    approve,
    enqueue,
    list_approved,
    list_pending,
    mark_published,
    reject,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_content(**overrides: object) -> QueuedContent:
    """Create a QueuedContent with sensible defaults."""
    defaults = {
        "piece_id": "test1234",
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "topic": "AI image generation tips",
        "text": "Here is some content text.",
        "reasoning": "Tutorials perform well on LinkedIn.",
    }
    defaults.update(overrides)
    return QueuedContent(**defaults)


@pytest.fixture()
def queue_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect QUEUE_DIR to a temp directory."""
    fake_dir = tmp_path / "content-queue"
    monkeypatch.setattr("holus.agents.marketing.content_queue.QUEUE_DIR", fake_dir)
    return fake_dir


# ---------------------------------------------------------------------------
# QueuedContent model
# ---------------------------------------------------------------------------


class TestQueuedContentModel:
    """Test the QueuedContent Pydantic model."""

    def test_defaults(self) -> None:
        c = _make_content()
        assert c.status == "pending_review"
        assert c.rejection_reason == ""
        assert isinstance(c.generated_at, datetime)

    def test_auto_piece_id(self) -> None:
        c = QueuedContent(
            product="genpeli",
            platform="instagram",
            content_type="demo",
            topic="test",
            text="hello",
            reasoning="why",
        )
        assert len(c.piece_id) == 8

    def test_custom_fields(self) -> None:
        c = _make_content(product="invoz", platform="twitter", status="approved")
        assert c.product == "invoz"
        assert c.platform == "twitter"
        assert c.status == "approved"


# ---------------------------------------------------------------------------
# enqueue()
# ---------------------------------------------------------------------------


class TestEnqueue:
    """Test enqueue() — file creation and content."""

    def test_creates_directory_and_file(self, queue_dir: Path) -> None:
        c = _make_content()
        path = enqueue(c)
        assert path.exists()
        assert path.parent == queue_dir
        assert path.name == "test1234.yaml"

    def test_yaml_content_matches(self, queue_dir: Path) -> None:
        c = _make_content(piece_id="abc12345")
        path = enqueue(c)
        data = yaml.safe_load(path.read_text())
        assert data["piece_id"] == "abc12345"
        assert data["product"] == "pilaster"
        assert data["platform"] == "linkedin"
        assert data["status"] == "pending_review"
        assert data["text"] == "Here is some content text."

    def test_datetime_serialized_as_iso(self, queue_dir: Path) -> None:
        c = _make_content()
        path = enqueue(c)
        data = yaml.safe_load(path.read_text())
        # Should be a string, not a datetime object
        assert isinstance(data["generated_at"], str)
        # Should parse back
        datetime.fromisoformat(data["generated_at"])

    def test_enqueue_overwrites_same_id(self, queue_dir: Path) -> None:
        c1 = _make_content(text="version 1")
        c2 = _make_content(text="version 2")
        enqueue(c1)
        path = enqueue(c2)
        data = yaml.safe_load(path.read_text())
        assert data["text"] == "version 2"

    def test_enqueue_multiple_pieces(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="aaa11111"))
        enqueue(_make_content(piece_id="bbb22222"))
        files = list(queue_dir.glob("*.yaml"))
        assert len(files) == 2


# ---------------------------------------------------------------------------
# list_pending()
# ---------------------------------------------------------------------------


class TestListPending:
    """Test list_pending() — filters pending_review items."""

    def test_empty_when_no_dir(self, queue_dir: Path) -> None:
        # Directory doesn't exist yet
        assert list_pending() == []

    def test_returns_pending_items(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="p1"))
        enqueue(_make_content(piece_id="p2"))
        result = list_pending()
        assert len(result) == 2
        assert all(c.status == "pending_review" for c in result)

    def test_excludes_approved(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="p1"))
        enqueue(_make_content(piece_id="ap1"))
        approve("ap1")
        result = list_pending()
        assert len(result) == 1
        assert result[0].piece_id == "p1"

    def test_excludes_rejected(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="p1"))
        enqueue(_make_content(piece_id="rj1"))
        reject("rj1", reason="bad")
        result = list_pending()
        assert len(result) == 1
        assert result[0].piece_id == "p1"

    def test_skips_corrupt_files(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="good1"))
        queue_dir.mkdir(parents=True, exist_ok=True)
        (queue_dir / "bad.yaml").write_text("not: valid: yaml: [")
        result = list_pending()
        assert len(result) == 1
        assert result[0].piece_id == "good1"

    def test_sorted_by_filename(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="zzz00000"))
        enqueue(_make_content(piece_id="aaa00000"))
        result = list_pending()
        assert result[0].piece_id == "aaa00000"
        assert result[1].piece_id == "zzz00000"


# ---------------------------------------------------------------------------
# list_approved()
# ---------------------------------------------------------------------------


class TestListApproved:
    """Test list_approved() — filters approved items."""

    def test_empty_when_no_dir(self, queue_dir: Path) -> None:
        assert list_approved() == []

    def test_returns_only_approved(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="a1"))
        enqueue(_make_content(piece_id="a2"))
        enqueue(_make_content(piece_id="p1"))
        approve("a1")
        approve("a2")
        result = list_approved()
        assert len(result) == 2
        ids = {c.piece_id for c in result}
        assert ids == {"a1", "a2"}

    def test_excludes_pending_and_rejected(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="pend"))
        enqueue(_make_content(piece_id="rej1"))
        enqueue(_make_content(piece_id="appr"))
        reject("rej1")
        approve("appr")
        result = list_approved()
        assert len(result) == 1
        assert result[0].piece_id == "appr"


# ---------------------------------------------------------------------------
# approve()
# ---------------------------------------------------------------------------


class TestApprove:
    """Test approve() — status transition to approved."""

    def test_approve_changes_status(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="x1"))
        approve("x1")
        data = yaml.safe_load((queue_dir / "x1.yaml").read_text())
        assert data["status"] == "approved"

    def test_approve_preserves_other_fields(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="x2", text="keep this"))
        approve("x2")
        data = yaml.safe_load((queue_dir / "x2.yaml").read_text())
        assert data["text"] == "keep this"
        assert data["product"] == "pilaster"

    def test_approve_missing_raises(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError, match="nope"):
            approve("nope")


# ---------------------------------------------------------------------------
# reject()
# ---------------------------------------------------------------------------


class TestReject:
    """Test reject() — status transition to rejected."""

    def test_reject_changes_status(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="r1"))
        reject("r1")
        data = yaml.safe_load((queue_dir / "r1.yaml").read_text())
        assert data["status"] == "rejected"

    def test_reject_stores_reason(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="r2"))
        reject("r2", reason="Off brand")
        data = yaml.safe_load((queue_dir / "r2.yaml").read_text())
        assert data["rejection_reason"] == "Off brand"

    def test_reject_default_empty_reason(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="r3"))
        reject("r3")
        data = yaml.safe_load((queue_dir / "r3.yaml").read_text())
        assert data["rejection_reason"] == ""

    def test_reject_missing_raises(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError, match="gone"):
            reject("gone")


# ---------------------------------------------------------------------------
# mark_published()
# ---------------------------------------------------------------------------


class TestMarkPublished:
    """Test mark_published() — status transition to published."""

    def test_mark_published_changes_status(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="pub1"))
        approve("pub1")
        mark_published("pub1", post_id="post_999")
        data = yaml.safe_load((queue_dir / "pub1.yaml").read_text())
        assert data["status"] == "published"

    def test_mark_published_stores_post_id(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="pub2"))
        mark_published("pub2", post_id="ext_abc")
        data = yaml.safe_load((queue_dir / "pub2.yaml").read_text())
        assert data["post_id"] == "ext_abc"

    def test_mark_published_stores_timestamp(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="pub3"))
        mark_published("pub3", post_id="id1")
        data = yaml.safe_load((queue_dir / "pub3.yaml").read_text())
        assert "published_at" in data
        # Should parse as ISO datetime
        datetime.fromisoformat(data["published_at"])

    def test_mark_published_missing_raises(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError, match="nope"):
            mark_published("nope", post_id="x")


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    """Test complete content lifecycle: enqueue → approve → publish."""

    def test_pending_to_approved_to_published(self, queue_dir: Path) -> None:
        c = _make_content(piece_id="life1")
        enqueue(c)

        # Starts pending
        assert len(list_pending()) == 1
        assert len(list_approved()) == 0

        # Approve
        approve("life1")
        assert len(list_pending()) == 0
        assert len(list_approved()) == 1

        # Publish
        mark_published("life1", post_id="social_123")
        assert len(list_approved()) == 0
        data = yaml.safe_load((queue_dir / "life1.yaml").read_text())
        assert data["status"] == "published"
        assert data["post_id"] == "social_123"

    def test_pending_to_rejected(self, queue_dir: Path) -> None:
        enqueue(_make_content(piece_id="life2"))
        reject("life2", reason="Not aligned with brand")
        assert len(list_pending()) == 0
        assert len(list_approved()) == 0

    def test_multiple_items_mixed_statuses(self, queue_dir: Path) -> None:
        for i in range(5):
            enqueue(_make_content(piece_id=f"mix{i:05d}"))

        approve("mix00001")
        approve("mix00003")
        reject("mix00002")

        assert len(list_pending()) == 2  # mix00000, mix00004
        assert len(list_approved()) == 2  # mix00001, mix00003
