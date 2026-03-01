"""Tests for holus.agents.marketing.video_queue and review_videos.

Tests cover:
  - QueuedVideo model construction and defaults
  - Enqueue / list_pending / list_approved
  - Approve / reject / mark_published status transitions
  - FileNotFoundError on missing pieces
  - YAML round-trip with datetime serialization
  - review_videos CLI display, show, approve, reject paths
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

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
# Helpers
# ---------------------------------------------------------------------------


def _make_video(**overrides: object) -> QueuedVideo:
    """Build a QueuedVideo with sensible defaults."""
    defaults = {
        "piece_id": "abc12345",
        "job_id": "genpeli-job-001",
        "preview_url": "http://localhost:8100/v1/jobs/001/preview",
        "product": "pilaster",
        "platform": "tiktok",
        "content_type": "video_reel",
        "topic": "ComfyUI quick-start tutorial",
        "reasoning": "Tutorial posts get 4x engagement",
        "decision": {"product": "pilaster", "platform": "tiktok"},
    }
    defaults.update(overrides)
    return QueuedVideo(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestQueuedVideoModel:
    def test_defaults(self) -> None:
        video = _make_video()
        assert video.status == "pending_review"
        assert video.rejection_reason == ""
        assert isinstance(video.generated_at, datetime)
        assert video.decision == {"product": "pilaster", "platform": "tiktok"}

    def test_auto_piece_id(self) -> None:
        video = QueuedVideo(
            job_id="j1",
            preview_url="http://preview",
            product="genpeli",
            platform="linkedin",
            content_type="demo",
            topic="Demo",
            reasoning="Test",
        )
        assert len(video.piece_id) == 8

    def test_custom_status(self) -> None:
        video = _make_video(status="approved")
        assert video.status == "approved"


# ---------------------------------------------------------------------------
# Queue operations (file-based)
# ---------------------------------------------------------------------------


class TestEnqueueVideo:
    def test_creates_file(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            video = _make_video()
            path = enqueue_video(video)

            assert path.exists()
            assert path.name == "abc12345.yaml"

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            video = _make_video()
            path = enqueue_video(video)

            data = yaml.safe_load(path.read_text())
            assert data["piece_id"] == "abc12345"
            assert data["job_id"] == "genpeli-job-001"
            assert data["preview_url"] == "http://localhost:8100/v1/jobs/001/preview"
            assert data["product"] == "pilaster"
            assert data["status"] == "pending_review"
            # datetime is stored as isoformat string
            assert isinstance(data["generated_at"], str)

    def test_creates_directory(self, tmp_path: Path) -> None:
        queue_dir = tmp_path / "nested" / "queue"
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", queue_dir):
            video = _make_video()
            path = enqueue_video(video)
            assert path.exists()
            assert queue_dir.exists()


class TestListPendingVideos:
    def test_empty_directory(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            assert list_pending_videos() == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", missing):
            assert list_pending_videos() == []

    def test_returns_pending_only(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            enqueue_video(_make_video(piece_id="v2"))
            # Approve v2
            approve_video("v2")

            pending = list_pending_videos()
            assert len(pending) == 1
            assert pending[0].piece_id == "v1"

    def test_sorted_by_filename(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="bbb"))
            enqueue_video(_make_video(piece_id="aaa"))

            pending = list_pending_videos()
            assert [v.piece_id for v in pending] == ["aaa", "bbb"]

    def test_skips_malformed_files(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="good"))
            # Write a malformed file
            (tmp_path / "bad.yaml").write_text("not: [valid: yaml: {")

            pending = list_pending_videos()
            assert len(pending) == 1
            assert pending[0].piece_id == "good"


class TestListApprovedVideos:
    def test_returns_approved_only(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            enqueue_video(_make_video(piece_id="v2"))
            approve_video("v1")

            approved = list_approved_videos()
            assert len(approved) == 1
            assert approved[0].piece_id == "v1"


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestApproveVideo:
    def test_approve(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            approve_video("v1")

            data = yaml.safe_load((tmp_path / "v1.yaml").read_text())
            assert data["status"] == "approved"

    def test_not_found(self, tmp_path: Path) -> None:
        with (
            patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path),
            pytest.raises(FileNotFoundError, match="v-missing"),
        ):
            approve_video("v-missing")


class TestRejectVideo:
    def test_reject_with_reason(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            reject_video("v1", "Poor audio quality")

            data = yaml.safe_load((tmp_path / "v1.yaml").read_text())
            assert data["status"] == "rejected"
            assert data["rejection_reason"] == "Poor audio quality"

    def test_reject_no_reason(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            reject_video("v1")

            data = yaml.safe_load((tmp_path / "v1.yaml").read_text())
            assert data["status"] == "rejected"
            assert data["rejection_reason"] == ""

    def test_not_found(self, tmp_path: Path) -> None:
        with (
            patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path),
            pytest.raises(FileNotFoundError),
        ):
            reject_video("v-missing")


class TestMarkPublished:
    def test_mark_published(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            approve_video("v1")
            mark_published("v1", "post-12345")

            data = yaml.safe_load((tmp_path / "v1.yaml").read_text())
            assert data["status"] == "published"
            assert data["post_id"] == "post-12345"
            assert "published_at" in data

    def test_not_found(self, tmp_path: Path) -> None:
        with (
            patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path),
            pytest.raises(FileNotFoundError),
        ):
            mark_published("v-missing", "post-123")


# ---------------------------------------------------------------------------
# Review CLI tests
# ---------------------------------------------------------------------------


class TestReviewVideosCLI:
    def test_display_pending_empty(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            from holus.agents.marketing.review_videos import display_pending

            display_pending()
            captured = capsys.readouterr()
            assert "No pending videos" in captured.out

    def test_display_pending_with_items(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1", topic="Test topic"))

            # Force a wide console so Rich doesn't truncate table columns
            from rich.console import Console

            import holus.agents.marketing.review_videos as rv

            rv.console = Console(width=200)

            rv.display_pending()
            captured = capsys.readouterr()
            assert "v1" in captured.out
            assert "Test topic" in captured.out

    def test_show_video(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1", topic="Demo topic"))
            from holus.agents.marketing.review_videos import show_video

            show_video("v1")
            captured = capsys.readouterr()
            assert "Demo topic" in captured.out
            assert "genpeli-job-001" in captured.out

    def test_show_video_not_found(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            from holus.agents.marketing.review_videos import show_video

            with pytest.raises(SystemExit):
                show_video("v-missing")

    def test_approve_cli(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            from holus.agents.marketing.review_videos import approve_video_cli

            approve_video_cli("v1")
            captured = capsys.readouterr()
            assert "Approved" in captured.out

            data = yaml.safe_load((tmp_path / "v1.yaml").read_text())
            assert data["status"] == "approved"

    def test_approve_cli_not_found(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            from holus.agents.marketing.review_videos import approve_video_cli

            with pytest.raises(SystemExit):
                approve_video_cli("v-missing")

    def test_reject_cli(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            enqueue_video(_make_video(piece_id="v1"))
            from holus.agents.marketing.review_videos import reject_video_cli

            reject_video_cli("v1", "Bad quality")
            captured = capsys.readouterr()
            assert "Rejected" in captured.out
            assert "Bad quality" in captured.out

    def test_reject_cli_not_found(self, tmp_path: Path) -> None:
        with patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path):
            from holus.agents.marketing.review_videos import reject_video_cli

            with pytest.raises(SystemExit):
                reject_video_cli("v-missing", "reason")

    def test_main_no_args(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with (
            patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path),
            patch("sys.argv", ["review_videos"]),
        ):
            from holus.agents.marketing.review_videos import main

            main()
            captured = capsys.readouterr()
            assert "No pending videos" in captured.out

    def test_main_approve(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with (
            patch("holus.agents.marketing.video_queue.VIDEO_QUEUE_DIR", tmp_path),
            patch("sys.argv", ["review_videos", "--approve", "v1"]),
        ):
            enqueue_video(_make_video(piece_id="v1"))
            from holus.agents.marketing.review_videos import main

            main()
            captured = capsys.readouterr()
            assert "Approved" in captured.out
