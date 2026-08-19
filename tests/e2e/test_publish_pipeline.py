"""End-to-end test: content queue → humanize → approve → publish → verify.

Exercises the full pipeline with real YAML files on disk, mocking only the
external social-media API call.  Validates that content moves through every
lifecycle state: pending_review → humanized → approved → published (or failed).
SPEC-032: content must be humanized before approval.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

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


def _outbox_records(queue_dir: Path) -> list[dict]:
    outbox_dir = queue_dir.parent / "lineage" / "outbox"
    return [json.loads(path.read_text(encoding="utf-8")) for path in outbox_dir.glob("*.json")]


def _assert_contained_publish_state(data: dict) -> None:
    assert data["status"] == "approved"
    assert data["publish_status"] == "contained"
    assert data["dispatch_request_id"]
    assert "post_id" not in data
    assert "published_at" not in data


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
    # The guarded API boundary reads the same queue files when publish_all dispatches.
    monkeypatch.setattr("holus.api.routes.content.CONTENT_QUEUE_DIR", q)
    return q


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

    def test_publish_all_records_contained_intent_without_success_state(
        self, queue_dir, monkeypatch
    ):
        """Full pipeline: enqueue → humanize → approve → publish_all → contained."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="pub1"))
        _humanize_and_approve("pub1")

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        data = _read_yaml(queue_dir / "pub1.yaml")
        _assert_contained_publish_state(data)
        social_client_cls.assert_not_called()
        [intent] = _outbox_records(queue_dir)
        assert intent["status"] == "contained"
        assert intent["external_id"] is None
        assert intent["payload"]["platforms"] == ["linkedin"]
        assert intent["payload"]["style"] == "raw"
        assert "AI image platform" in intent["payload"]["content"]

    def test_publish_all_has_no_local_failure_result_without_delivery(self, queue_dir, monkeypatch):
        """Contained publish does not synthesize obsolete failed delivery state."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="fail1"))
        _humanize_and_approve("fail1")

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        data = _read_yaml(queue_dir / "fail1.yaml")
        _assert_contained_publish_state(data)
        social_client_cls.assert_not_called()

    def test_publish_all_handles_exception(self, queue_dir, monkeypatch):
        """A patched client seam is not reached, so no local success state is written."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="err1"))
        _humanize_and_approve("err1")

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        data = _read_yaml(queue_dir / "err1.yaml")
        _assert_contained_publish_state(data)
        social_client_cls.assert_not_called()


class TestReviewGateContract:
    """SPEC-032 explicit review gate: humanize → approve before any publish attempt.

    Contract: publish_all only touches approved content and never constructs a live
    Holus Social API client.
    """

    def test_cannot_approve_without_humanization(self, queue_dir):
        """Approve is blocked until content passes the humanization gate."""
        enqueue(_make_content(piece_id="gate1"))

        with pytest.raises(ValueError, match="must be humanized first"):
            approve("gate1")

        data = _read_yaml(queue_dir / "gate1.yaml")
        assert data["status"] == "pending_review"

    def test_humanize_rejects_excessive_edit_distance(self, queue_dir):
        """Humanize rejects rewrites that exceed the SPEC-032 edit-distance limit."""
        enqueue(
            _make_content(
                piece_id="gate2",
                text="Original text about AI engineering and building reliable systems.",
            )
        )

        with pytest.raises(ValueError, match=r"exceeds.*limit"):
            humanize(
                "gate2",
                "Completely different topic about cooking pasta and gardening tips.",
            )

        data = _read_yaml(queue_dir / "gate2.yaml")
        assert data["status"] == "pending_review"

    def test_pending_review_not_published(self, queue_dir, monkeypatch):
        """Content still in pending_review must not be published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")
        enqueue(_make_content(piece_id="gate3"))

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        social_client_cls.assert_not_called()
        assert _read_yaml(queue_dir / "gate3.yaml")["status"] == "pending_review"

    def test_humanized_but_unapproved_not_published(self, queue_dir, monkeypatch):
        """Humanized content that was never approved must not be published."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")
        enqueue(_make_content(piece_id="gate4"))
        humanize(
            "gate4",
            "I built an AI image platform with memory! Here is what I learned.",
        )

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        social_client_cls.assert_not_called()
        assert _read_yaml(queue_dir / "gate4.yaml")["status"] == "humanized"

    def test_rejected_content_never_published(self, queue_dir, monkeypatch):
        """Rejected content is skipped by publish_all."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")
        enqueue(_make_content(piece_id="gate5"))
        reject("gate5", reason="off-brand")

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        social_client_cls.assert_not_called()
        assert _read_yaml(queue_dir / "gate5.yaml")["status"] == "rejected"

    def test_publish_all_never_instantiates_live_httpx(self, queue_dir, monkeypatch):
        """Contract: contained publish_all constructs no Social API client or live httpx."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")
        enqueue(_make_content(piece_id="gate6"))
        _humanize_and_approve("gate6")

        with (
            patch(
                "holus.api.routes.content.HolusSocialAPIClient",
                side_effect=AssertionError("social client constructed"),
            ) as social_client_cls,
            patch("httpx.AsyncClient") as live_httpx,
        ):
            asyncio.run(publish_all())

        live_httpx.assert_not_called()
        social_client_cls.assert_not_called()
        _assert_contained_publish_state(_read_yaml(queue_dir / "gate6.yaml"))

    def test_lifecycle_transitions_are_sequential(self, queue_dir):
        """Contract: pending_review → humanized → approved → published."""
        enqueue(_make_content(piece_id="lifecycle1"))
        assert _read_yaml(queue_dir / "lifecycle1.yaml")["status"] == "pending_review"

        humanize(
            "lifecycle1",
            "I built an AI image platform with memory! Here is what I learned.",
        )
        assert _read_yaml(queue_dir / "lifecycle1.yaml")["status"] == "humanized"

        approve("lifecycle1")
        assert _read_yaml(queue_dir / "lifecycle1.yaml")["status"] == "approved"

        mark_published("lifecycle1", "job-contract")
        data = _read_yaml(queue_dir / "lifecycle1.yaml")
        assert data["status"] == "published"
        assert data["post_id"] == "job-contract"


class TestMultiPiecePipeline:
    """Multiple content pieces flowing through the pipeline together."""

    def test_publish_multiple_approved(self, queue_dir, monkeypatch):
        """Multiple approved pieces all record contained dispatch intents in one run."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        pieces = [
            _make_content(piece_id="m1", platform="linkedin"),
            _make_content(piece_id="m2", platform="twitter", text="Short tweet about AI."),
            _make_content(piece_id="m3", platform="threads", text="Thread about building."),
        ]
        for p in pieces:
            enqueue(p)
            _humanize_and_approve(p.piece_id, p.text)

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        for pid in ("m1", "m2", "m3"):
            data = _read_yaml(queue_dir / f"{pid}.yaml")
            _assert_contained_publish_state(data)

        social_client_cls.assert_not_called()
        assert len(_outbox_records(queue_dir)) == 3

    def test_mixed_success_and_failure(self, queue_dir, monkeypatch):
        """No per-piece success/failure can occur while delivery is contained."""
        monkeypatch.setenv("POSTING_API_KEY", "test-key-123")

        enqueue(_make_content(piece_id="ok1", platform="linkedin"))
        enqueue(_make_content(piece_id="bad1", platform="twitter", text="Short tweet."))
        _humanize_and_approve("ok1")
        _humanize_and_approve("bad1", "Short tweet.")

        with patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls:
            asyncio.run(publish_all())

        _assert_contained_publish_state(_read_yaml(queue_dir / "ok1.yaml"))
        _assert_contained_publish_state(_read_yaml(queue_dir / "bad1.yaml"))
        social_client_cls.assert_not_called()
        assert len(_outbox_records(queue_dir)) == 2


class TestPublishBoundary:
    """publish_all delegates only through the guarded Social API boundary."""

    def test_publish_without_api_key_uses_mocked_social_api_boundary(self, queue_dir, monkeypatch):
        """No API configuration can cause a live client to be constructed."""
        monkeypatch.delenv("POSTING_API_KEY", raising=False)
        enqueue(_make_content(piece_id="nokey"))
        _humanize_and_approve("nokey")

        with (
            patch(
                "holus.api.routes.content.HolusSocialAPIClient",
                side_effect=AssertionError("social client constructed"),
            ) as social_client_cls,
            patch("httpx.AsyncClient") as live_httpx,
        ):
            asyncio.run(publish_all())

        live_httpx.assert_not_called()
        social_client_cls.assert_not_called()
        _assert_contained_publish_state(_read_yaml(queue_dir / "nokey.yaml"))


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
