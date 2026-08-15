"""End-to-end manual publish pipeline tests.

Tests the full manual flow: enqueue → humanize → approve → publish → verify.
Covers the SPEC-032 humanization gate and publish_approved module together.
Uses temp queue directories and mocked social media client.
"""

from __future__ import annotations

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
)
from holus.agents.marketing.publish_approved import publish_all

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def temp_queue(tmp_path: Path, monkeypatch):
    """Create a temp queue shared by the queue owner and guarded API boundary."""
    queue_dir = tmp_path / "content-queue"
    queue_dir.mkdir()
    monkeypatch.setattr("holus.agents.marketing.content_queue.QUEUE_DIR", queue_dir)
    monkeypatch.setattr("holus.api.routes.content.CONTENT_QUEUE_DIR", queue_dir)
    return queue_dir


def _make_content(
    *,
    piece_id: str = "test0001",
    platform: str = "linkedin",
    text: str = "AI engineering is about shipping systems that learn, not just models that predict.",
) -> QueuedContent:
    """Helper: create a QueuedContent with sensible defaults."""
    return QueuedContent(
        piece_id=piece_id,
        product="pilaster",
        platform=platform,
        content_type="text_post",
        topic="AI engineering insights",
        text=text,
        reasoning="Authority-building post targeting AI engineering leaders",
        generated_at=datetime.now(tz=UTC),
    )


def _outbox_records(queue_dir: Path) -> list[dict]:
    outbox_dir = queue_dir.parent / "lineage" / "outbox"
    return [json.loads(path.read_text(encoding="utf-8")) for path in outbox_dir.glob("*.json")]


def _assert_contained_publish_state(raw: dict) -> None:
    assert raw["status"] == "approved"
    assert raw["publish_status"] == "contained"
    assert raw["dispatch_request_id"]
    assert "post_id" not in raw
    assert "published_at" not in raw


# ---------------------------------------------------------------------------
# Full manual pipeline: enqueue → humanize → approve → publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_manual_pipeline(temp_queue: Path):
    """Full pipeline: enqueue → humanize → approve → publish → verify status."""
    content = _make_content()

    # Step 1: Enqueue
    path = enqueue(content)
    assert path.exists()
    pending = list_pending()
    assert len(pending) == 1
    assert pending[0].piece_id == "test0001"
    assert pending[0].status == "pending_review"

    # Step 2: Humanize (small edit, within 40% limit)
    humanized = humanize(
        "test0001",
        "AI engineering is about shipping systems that learn — not just models that predict.",
    )
    assert humanized.status == "humanized"
    assert humanized.edit_distance is not None
    assert humanized.edit_distance <= 0.40

    # Step 3: Approve
    approve("test0001")
    approved = list_approved()
    assert len(approved) == 1
    assert approved[0].status == "approved"

    # Step 4: Publish through the route boundary. P0 containment must not construct a client.
    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls,
    ):
        await publish_all()

    # Step 5: Verify final contained state
    import yaml

    final_data = yaml.safe_load(path.read_text())
    _assert_contained_publish_state(final_data)
    social_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_publish_uses_humanized_text_when_available(temp_queue: Path):
    """Publish should use humanized_text if present, falling back to original text."""
    content = _make_content(
        piece_id="htext01",
        text="Original AI engineering post content here.",
    )
    enqueue(content)

    humanize(
        "htext01",
        "Original AI engineering post content updated.",
    )
    approve("htext01")

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls,
    ):
        await publish_all()

    social_client_cls.assert_not_called()
    [intent] = _outbox_records(temp_queue)
    assert intent["payload"]["content"] == "Original AI engineering post content updated."
    assert intent["payload"]["platforms"] == ["linkedin"]
    assert intent["status"] == "contained"


@pytest.mark.asyncio
async def test_cannot_approve_without_humanization(temp_queue: Path):
    """SPEC-032: approve() must fail if content hasn't been humanized."""
    content = _make_content(piece_id="nohuman1")
    enqueue(content)

    with pytest.raises(ValueError, match="must be humanized first"):
        approve("nohuman1")


@pytest.mark.asyncio
async def test_humanize_rejects_large_edits(temp_queue: Path):
    """SPEC-032: humanize() rejects edits exceeding 40% edit distance."""
    content = _make_content(
        piece_id="bigedit1",
        text="Original text about AI engineering and building systems.",
    )
    enqueue(content)

    with pytest.raises(ValueError, match=r"exceeds.*limit"):
        humanize(
            "bigedit1",
            "Completely different text about cooking recipes and garden tips for summer.",
        )


@pytest.mark.asyncio
async def test_pipeline_with_multiple_pieces(temp_queue: Path):
    """Multiple pieces flow through the pipeline independently."""
    # Enqueue 3 pieces
    for i in range(3):
        content = _make_content(
            piece_id=f"multi{i:03d}",
            text=f"Post {i}: AI systems that ship are better than AI systems that don't.",
        )
        enqueue(content)

    # Humanize and approve only the first two
    humanize(
        "multi000",
        "Post 0: AI systems that ship are better than those that don't.",
    )
    approve("multi000")

    humanize(
        "multi001",
        "Post 1: AI systems that ship are better than those that don't.",
    )
    approve("multi001")

    # Third stays pending_review
    approved = list_approved()
    assert len(approved) == 2

    pending = list_pending()
    assert len(pending) == 1
    assert pending[0].piece_id == "multi002"


@pytest.mark.asyncio
async def test_publish_without_api_key_stays_at_mocked_social_api_boundary(temp_queue: Path):
    """This integration test never constructs a live social API client."""
    content = _make_content(piece_id="nokey001")
    enqueue(content)
    humanize("nokey001", "AI engineering is about shipping systems that learn — not just models.")
    approve("nokey001")

    with patch(
        "holus.api.routes.content.HolusSocialAPIClient",
        side_effect=AssertionError("social client constructed"),
    ) as social_client_cls:
        await publish_all()

    social_client_cls.assert_not_called()
    final_data = yaml.safe_load((temp_queue / "nokey001.yaml").read_text())
    _assert_contained_publish_state(final_data)


@pytest.mark.asyncio
async def test_publish_handles_api_failure_gracefully(temp_queue: Path):
    """If the social media API returns a failed target, the piece stays approved."""
    content = _make_content(piece_id="fail0001")
    enqueue(content)
    humanize("fail0001", "AI engineering is about shipping systems that learn — not models.")
    approve("fail0001")

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls,
    ):
        await publish_all()

    # Piece remains approved because P0 contains delivery before any API result can exist.
    import yaml

    path = temp_queue / "fail0001.yaml"
    final_data = yaml.safe_load(path.read_text())
    _assert_contained_publish_state(final_data)
    social_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_publish_with_media_attachment(temp_queue: Path):
    """Content with a managed rendered image reaches the guarded publish boundary."""
    media_path = temp_queue.parent / "rendered-content" / "infographic.png"
    media_path.parent.mkdir()
    media_path.write_bytes(b"test image")

    content = _make_content(piece_id="media001")
    content.rendered_image_path = str(media_path)
    content.media_type = "image"
    enqueue(content)
    humanize("media001", "AI engineering is about shipping systems that learn — not models.")
    approve("media001")

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            side_effect=AssertionError("social client constructed"),
        ) as social_client_cls,
    ):
        await publish_all()

    social_client_cls.assert_not_called()
    [intent] = _outbox_records(temp_queue)
    assert intent["payload"]["media_url"] == str(media_path)
    assert intent["payload"]["media_type"] == "image"
    assert intent["status"] == "contained"
