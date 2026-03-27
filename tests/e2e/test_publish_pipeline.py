"""End-to-end test: content queue → humanize → approve → publish → verify.

Exercises the full pipeline with real YAML files on disk, mocking only the
external social-media API call.  Validates that content moves through every
lifecycle state: pending_review → humanized → approved → published (or failed).
SPEC-032: content must be humanized before approval.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from holus.agents.marketing.content_queue import (
    QueuedContent,
    approve,
    enqueue,
    humanize,
    list_approved,
    list_pending,
    mark_published,
    reject,
)
from holus.agents.marketing.publish_approved import publish_all
from holus.integrations.social_media import PublishResult, PublishTarget

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_content(
    piece_id: str = "e2e-test1",
    platform: str = "linkedin",
    text: str = "I built an AI image platform with memory. Here is what I learned.",
) -> QueuedContent:
    return QueuedContent(
        piece_id=piece_id,
        product="pilaster",
        platform=platform,
        content_type="tutorial",
        topic="Builder story about Pilaster architecture",
        text=text,
        reasoning="Builder stories demonstrate consulting expertise",
        generated_at=datetime(2026, 3, 2, 14, 0, tzinfo=UTC),
        status="pending_review",
    )


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _humanize_and_approve(
    piece_id: str, text: str = "I built an AI image platform with memory. Here is what I learned."
) -> None:
    """SPEC-032: content must be humanized before approval."""
    # Humanized text must differ slightly but stay within 40% edit distance
    humanized = text.rstrip(".") + "!" if len(text) < 40 else text.rstrip(".") + " — edited."
    humanize(piece_id, humanized)
    approve(piece_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def queue_dir(tmp_path, monkeypatch):
    """Redirect the content queue to a temp directory."""
    q = tmp_path / "content-queue"
    q.mkdir()
    monkeypatch.setattr(
        "holus.agents.marketing.content_queue.QUEUE_DIR",
        q,
    )
    # publish_approved imports list_approved and mark_published from content_queue,
    # so the monkeypatch on QUEUE_DIR is already in effect for those functions.
    return q


@pytest.fixture()
def mock_publish_success():
    """Mock SocialMediaClient.publish that always succeeds."""
    return PublishResult(
        publish_id="job-42",
        targets=[
            PublishTarget(
                platform="linkedin",
                account="camilo",
                language="en",
                status="published",
                job_id=42,
            )
        ],
    )


@pytest.fixture()
def mock_publish_failure():
    """Mock SocialMediaClient.publish that reports a failure."""
    return PublishResult(
        publish_id="job-99",
        targets=[
            PublishTarget(
                platform="linkedin",
                account="camilo",
                language="en",
                status="failed",
                error="Rate limited by LinkedIn API",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Tests — Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPublishPipeline:
    """Happy-path: enqueue → approve → publish → verify published status."""

    def test_enqueue_creates_pending_yaml(self, queue_dir):
        content = _make_content()
        path = enqueue(content)

        assert path.exists()
        data = _read_yaml(path)
        assert data["status"] == "pending_review"
        assert data["piece_id"] == "e2e-test1"
        assert data["platform"] == "linkedin"

    def test_pending_list_shows_enqueued(self, queue_dir):
        enqueue(_make_content(piece_id="p1"))
        enqueue(_make_content(piece_id="p2"))

        pending = list_pending()
        assert len(pending) == 2
        assert {p.piece_id for p in pending} == {"p1", "p2"}

    def test_approve_changes_status(self, queue_dir):
        enqueue(_make_content(piece_id="ap1"))
        humanize(
            "ap1", "I built an AI image platform with memory. Here is what I learned — edited."
        )
        approve("ap1")

        data = _read_yaml(queue_dir / "ap1.yaml")
        assert data["status"] == "approved"

    def test_reject_changes_status(self, queue_dir):
        enqueue(_make_content(piece_id="rj1"))
        reject("rj1", reason="Tone doesn't match brand voice")

        data = _read_yaml(queue_dir / "rj1.yaml")
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Tone doesn't match brand voice"

    def test_approved_list_only_shows_approved(self, queue_dir):
        enqueue(_make_content(piece_id="a1"))
        enqueue(_make_content(piece_id="a2"))
        enqueue(_make_content(piece_id="a3"))

        _humanize_and_approve("a1")
        reject("a3", reason="off-brand")

        approved = list_approved()
        assert len(approved) == 1
        assert approved[0].piece_id == "a1"

    def test_publish_all_posts_and_marks_published(
        self, queue_dir, mock_publish_success, monkeypatch
    ):
        """Full pipeline: enqueue → humanize → approve → publish_all → status=published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="pub1"))
        _humanize_and_approve("pub1")

        mock_client = AsyncMock()
        mock_client.publish.return_value = mock_publish_success
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ):
            asyncio.run(publish_all())

        # Verify YAML status updated to published
        data = _read_yaml(queue_dir / "pub1.yaml")
        assert data["status"] == "published"
        assert data["post_id"] == "job-42"
        assert "published_at" in data

        # Verify the client was called with the right payload
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args[0][0]
        assert call_args.platforms == ["linkedin"]
        assert call_args.style == "raw"
        assert "AI image platform" in call_args.content

    def test_publish_all_handles_failure(self, queue_dir, mock_publish_failure, monkeypatch):
        """Failed publish does NOT mark content as published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="fail1"))
        _humanize_and_approve("fail1")

        mock_client = AsyncMock()
        mock_client.publish.return_value = mock_publish_failure
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ):
            asyncio.run(publish_all())

        # Status should still be approved (not published)
        data = _read_yaml(queue_dir / "fail1.yaml")
        assert data["status"] == "approved"
        assert "post_id" not in data

    def test_publish_all_handles_exception(self, queue_dir, monkeypatch):
        """Exception during publish does NOT mark content as published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="err1"))
        _humanize_and_approve("err1")

        mock_client = AsyncMock()
        mock_client.publish.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ):
            asyncio.run(publish_all())

        data = _read_yaml(queue_dir / "err1.yaml")
        assert data["status"] == "approved"


class TestMultiPiecePipeline:
    """Multiple content pieces flowing through the pipeline together."""

    def test_publish_multiple_approved(self, queue_dir, monkeypatch):
        """Multiple approved pieces all get published in one run."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        pieces = [
            _make_content(piece_id="m1", platform="linkedin"),
            _make_content(piece_id="m2", platform="twitter", text="Short tweet about AI."),
            _make_content(piece_id="m3", platform="threads", text="Thread about building."),
        ]
        for p in pieces:
            enqueue(p)
            _humanize_and_approve(p.piece_id, p.text)

        call_count = 0

        async def _mock_publish(request):
            nonlocal call_count
            call_count += 1
            return PublishResult(
                publish_id=f"job-{call_count}",
                targets=[
                    PublishTarget(
                        platform=request.platforms[0],
                        account="camilo",
                        language="en",
                        status="published",
                        job_id=call_count,
                    )
                ],
            )

        mock_client = AsyncMock()
        mock_client.publish = _mock_publish
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ):
            asyncio.run(publish_all())

        # All 3 should be published
        for pid in ("m1", "m2", "m3"):
            data = _read_yaml(queue_dir / f"{pid}.yaml")
            assert data["status"] == "published", f"{pid} should be published"
            assert "post_id" in data
            assert "published_at" in data

        assert call_count == 3

    def test_mixed_success_and_failure(self, queue_dir, monkeypatch):
        """One piece succeeds, one fails — only the successful one is marked published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="ok1", platform="linkedin"))
        enqueue(_make_content(piece_id="bad1", platform="twitter", text="Short tweet."))
        _humanize_and_approve("ok1")
        _humanize_and_approve("bad1", "Short tweet.")

        call_index = 0

        async def _mock_publish(request):
            nonlocal call_index
            call_index += 1
            platform = request.platforms[0]
            if platform == "twitter":
                return PublishResult(
                    publish_id="job-fail",
                    targets=[
                        PublishTarget(
                            platform="twitter",
                            status="failed",
                            error="API error",
                        )
                    ],
                )
            return PublishResult(
                publish_id="job-ok",
                targets=[
                    PublishTarget(
                        platform="linkedin",
                        status="published",
                        job_id=1,
                    )
                ],
            )

        mock_client = AsyncMock()
        mock_client.publish = _mock_publish
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ):
            asyncio.run(publish_all())

        assert _read_yaml(queue_dir / "ok1.yaml")["status"] == "published"
        assert _read_yaml(queue_dir / "bad1.yaml")["status"] == "approved"


class TestNoApiKey:
    """Publish exits with error when POSTING_API_KEY is missing."""

    def test_publish_exits_without_api_key(self, queue_dir, monkeypatch):
        monkeypatch.delenv("POSTING_API_KEY", raising=False)

        enqueue(_make_content(piece_id="nokey"))
        _humanize_and_approve("nokey")

        with pytest.raises(SystemExit) as exc_info:
            asyncio.run(publish_all())

        assert exc_info.value.code == 1

        # Content should not be modified
        data = _read_yaml(queue_dir / "nokey.yaml")
        assert data["status"] == "approved"


class TestMarkPublished:
    """Verify mark_published writes post_id and published_at to YAML."""

    def test_mark_published_adds_fields(self, queue_dir):
        enqueue(_make_content(piece_id="mp1"))
        _humanize_and_approve("mp1")
        mark_published("mp1", "job-777")

        data = _read_yaml(queue_dir / "mp1.yaml")
        assert data["status"] == "published"
        assert data["post_id"] == "job-777"
        assert "published_at" in data

    def test_mark_published_not_found(self, queue_dir):
        with pytest.raises(FileNotFoundError):
            mark_published("nonexistent", "job-000")


class TestQueueNotFound:
    """Operations on non-existent pieces raise FileNotFoundError."""

    def test_approve_not_found(self, queue_dir):
        with pytest.raises(FileNotFoundError):
            approve("ghost")

    def test_reject_not_found(self, queue_dir):
        with pytest.raises(FileNotFoundError):
            reject("ghost")
