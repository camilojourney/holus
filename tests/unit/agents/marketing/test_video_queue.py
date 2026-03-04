"""Tests for video_queue.py — enqueue, list, status transitions, YAML persistence.

Covers:
  - QueuedVideo model — defaults, field validation, serialization
  - enqueue_video() — saves YAML file, returns path, creates directory
  - list_pending_videos() — filters pending_review, handles empty dir, skips bad files
  - list_approved_videos() — filters approved only
  - approve_video() — status transition pending_review → approved
  - reject_video() — status transition pending_review → rejected, stores reason
  - mark_published() — status transition approved → published, stores post_id + timestamp
  - Edge cases — missing dir, missing file (FileNotFoundError), corrupt YAML, datetime parsing
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import yaml

from holus.agents.marketing.video_queue import (
    QueuedVideo,
    approve_video,
    enqueue_video,
    list_approved_videos,
    list_pending_videos,
    mark_published,
    reject_video,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_video(**overrides: object) -> QueuedVideo:
    """Create a QueuedVideo with sensible defaults."""
    defaults = {
        "piece_id": "test1234",
        "job_id": "genpeli-job-001",
        "preview_url": "https://example.com/preview/001.mp4",
        "product": "genpeli",
        "platform": "linkedin",
        "content_type": "demo",
        "topic": "AI video editing demo",
        "reasoning": "Demo videos perform well on LinkedIn.",
    }
    defaults.update(overrides)
    return QueuedVideo(**defaults)


@pytest.fixture()
def queue_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect VIDEO_QUEUE_DIR to a temp directory."""
    fake_dir = tmp_path / "video-queue"
    monkeypatch.setattr("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", fake_dir)
    return fake_dir


# ---------------------------------------------------------------------------
# QueuedVideo Model
# ---------------------------------------------------------------------------


class TestQueuedVideoModel:
    """Test QueuedVideo Pydantic model defaults and validation."""

    def test_defaults(self) -> None:
        v = _make_video()
        assert v.piece_id == "test1234"
        assert v.status == "pending_review"
        assert v.rejection_reason == ""
        assert v.decision == {}

    def test_auto_piece_id(self) -> None:
        v = QueuedVideo(
            job_id="j1",
            preview_url="https://example.com/v.mp4",
            product="genpeli",
            platform="linkedin",
            content_type="demo",
            topic="test",
            reasoning="test",
        )
        assert len(v.piece_id) == 8

    def test_generated_at_is_utc(self) -> None:
        v = _make_video()
        assert v.generated_at.tzinfo is not None

    def test_decision_dict(self) -> None:
        v = _make_video(decision={"product": "genpeli", "type": "demo"})
        assert v.decision["product"] == "genpeli"


# ---------------------------------------------------------------------------
# enqueue_video()
# ---------------------------------------------------------------------------


class TestEnqueueVideo:
    """Test enqueue_video saves YAML and creates directories."""

    def test_returns_path(self, queue_dir: Path) -> None:
        v = _make_video()
        path = enqueue_video(v)
        assert path == queue_dir / "test1234.yaml"
        assert path.exists()

    def test_creates_directory(self, queue_dir: Path) -> None:
        assert not queue_dir.exists()
        enqueue_video(_make_video())
        assert queue_dir.exists()

    def test_yaml_content(self, queue_dir: Path) -> None:
        v = _make_video(topic="special topic")
        path = enqueue_video(v)
        data = yaml.safe_load(path.read_text())
        assert data["topic"] == "special topic"
        assert data["status"] == "pending_review"
        assert data["job_id"] == "genpeli-job-001"

    def test_generated_at_serialized_as_iso(self, queue_dir: Path) -> None:
        v = _make_video()
        path = enqueue_video(v)
        data = yaml.safe_load(path.read_text())
        assert isinstance(data["generated_at"], str)
        datetime.fromisoformat(data["generated_at"])

    def test_multiple_enqueues(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="vid001"))
        enqueue_video(_make_video(piece_id="vid002"))
        assert len(list(queue_dir.glob("*.yaml"))) == 2


# ---------------------------------------------------------------------------
# list_pending_videos()
# ---------------------------------------------------------------------------


class TestListPendingVideos:
    """Test listing videos with pending_review status."""

    def test_empty_when_no_dir(self, queue_dir: Path) -> None:
        assert list_pending_videos() == []

    def test_returns_pending_only(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="p1"))
        enqueue_video(_make_video(piece_id="p2"))
        # Approve one
        approve_video("p1")
        pending = list_pending_videos()
        assert len(pending) == 1
        assert pending[0].piece_id == "p2"

    def test_sorted_by_filename(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="zzz"))
        enqueue_video(_make_video(piece_id="aaa"))
        pending = list_pending_videos()
        assert pending[0].piece_id == "aaa"
        assert pending[1].piece_id == "zzz"

    def test_skips_corrupt_yaml(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="good"))
        queue_dir.mkdir(parents=True, exist_ok=True)
        (queue_dir / "bad.yaml").write_text(":::not valid yaml[[[")
        pending = list_pending_videos()
        assert len(pending) == 1
        assert pending[0].piece_id == "good"

    def test_skips_yaml_missing_required_fields(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        (queue_dir / "incomplete.yaml").write_text(
            yaml.dump({"status": "pending_review", "piece_id": "incomplete"})
        )
        enqueue_video(_make_video(piece_id="valid"))
        pending = list_pending_videos()
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# list_approved_videos()
# ---------------------------------------------------------------------------


class TestListApprovedVideos:
    """Test listing videos with approved status."""

    def test_empty_when_none_approved(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="p1"))
        assert list_approved_videos() == []

    def test_returns_approved_only(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="a1"))
        enqueue_video(_make_video(piece_id="a2"))
        approve_video("a1")
        approved = list_approved_videos()
        assert len(approved) == 1
        assert approved[0].piece_id == "a1"

    def test_empty_dir(self, queue_dir: Path) -> None:
        assert list_approved_videos() == []


# ---------------------------------------------------------------------------
# approve_video()
# ---------------------------------------------------------------------------


class TestApproveVideo:
    """Test approve_video status transitions."""

    def test_sets_status_approved(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="v1"))
        approve_video("v1")
        data = yaml.safe_load((queue_dir / "v1.yaml").read_text())
        assert data["status"] == "approved"

    def test_file_not_found(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            approve_video("nonexistent")

    def test_preserves_other_fields(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="v2", topic="keep this"))
        approve_video("v2")
        data = yaml.safe_load((queue_dir / "v2.yaml").read_text())
        assert data["topic"] == "keep this"
        assert data["job_id"] == "genpeli-job-001"


# ---------------------------------------------------------------------------
# reject_video()
# ---------------------------------------------------------------------------


class TestRejectVideo:
    """Test reject_video status transitions."""

    def test_sets_status_rejected(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="r1"))
        reject_video("r1", reason="Low quality")
        data = yaml.safe_load((queue_dir / "r1.yaml").read_text())
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Low quality"

    def test_default_empty_reason(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="r2"))
        reject_video("r2")
        data = yaml.safe_load((queue_dir / "r2.yaml").read_text())
        assert data["rejection_reason"] == ""

    def test_file_not_found(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError):
            reject_video("missing")

    def test_preserves_other_fields(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="r3", product="pilaster"))
        reject_video("r3", reason="Off brand")
        data = yaml.safe_load((queue_dir / "r3.yaml").read_text())
        assert data["product"] == "pilaster"


# ---------------------------------------------------------------------------
# mark_published()
# ---------------------------------------------------------------------------


class TestMarkPublished:
    """Test mark_published status transitions."""

    def test_sets_status_published(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="pub1"))
        approve_video("pub1")
        mark_published("pub1", post_id="social-post-999")
        data = yaml.safe_load((queue_dir / "pub1.yaml").read_text())
        assert data["status"] == "published"
        assert data["post_id"] == "social-post-999"

    def test_adds_published_at(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="pub2"))
        mark_published("pub2", post_id="sp-1")
        data = yaml.safe_load((queue_dir / "pub2.yaml").read_text())
        assert "published_at" in data
        datetime.fromisoformat(data["published_at"])

    def test_file_not_found(self, queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError):
            mark_published("ghost", post_id="sp-1")

    def test_preserves_other_fields(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="pub3", reasoning="Good content"))
        mark_published("pub3", post_id="sp-2")
        data = yaml.safe_load((queue_dir / "pub3.yaml").read_text())
        assert data["reasoning"] == "Good content"


# ---------------------------------------------------------------------------
# Full Lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    """Test complete video queue lifecycle: enqueue → approve → publish."""

    def test_full_happy_path(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="life1"))
        assert len(list_pending_videos()) == 1
        assert len(list_approved_videos()) == 0

        approve_video("life1")
        assert len(list_pending_videos()) == 0
        assert len(list_approved_videos()) == 1

        mark_published("life1", post_id="final-post")
        assert len(list_approved_videos()) == 0
        data = yaml.safe_load((queue_dir / "life1.yaml").read_text())
        assert data["status"] == "published"

    def test_reject_path(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="rej1"))
        reject_video("rej1", reason="Not on brand")
        assert len(list_pending_videos()) == 0
        assert len(list_approved_videos()) == 0

    def test_multiple_videos_mixed_status(self, queue_dir: Path) -> None:
        enqueue_video(_make_video(piece_id="m1"))
        enqueue_video(_make_video(piece_id="m2"))
        enqueue_video(_make_video(piece_id="m3"))

        approve_video("m1")
        reject_video("m2", reason="Bad")
        # m3 stays pending

        assert len(list_pending_videos()) == 1
        assert list_pending_videos()[0].piece_id == "m3"
        assert len(list_approved_videos()) == 1
        assert list_approved_videos()[0].piece_id == "m1"
