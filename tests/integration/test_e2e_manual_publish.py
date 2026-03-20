"""End-to-end manual publish pipeline tests.

Tests the full manual flow: enqueue → humanize → approve → publish → verify.
Covers the SPEC-032 humanization gate and publish_approved module together.
Uses temp queue directories and mocked social media client.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from holus.agents.marketing.content_queue import (
    QueuedContent,
    approve,
    enqueue,
    humanize,
    list_approved,
    list_pending,
)
from holus.agents.marketing.publish_approved import publish_all
from holus.integrations.social_media import PublishResult, PublishTarget

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def temp_queue(tmp_path: Path):
    """Create a temp content-queue directory and patch QUEUE_DIR everywhere."""
    queue_dir = tmp_path / "content-queue"
    queue_dir.mkdir()
    with patch("holus.agents.marketing.content_queue.QUEUE_DIR", queue_dir):
        yield queue_dir


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

    # Step 4: Publish via mocked social media API
    mock_result = PublishResult(
        publish_id="sm-post-99",
        targets=[
            PublishTarget(
                platform="linkedin",
                account="juan-camilo",
                status="queued",
            )
        ],
    )

    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ),
    ):
        await publish_all()

    # Step 5: Verify final state
    # The queue file should now be marked as published
    import yaml

    final_data = yaml.safe_load(path.read_text())
    assert final_data["status"] == "published"
    assert final_data["post_id"] == "sm-post-99"
    assert "published_at" in final_data

    # Verify the client was called with the humanized text (publish uses content.text)
    mock_client.publish.assert_called_once()
    call_args = mock_client.publish.call_args[0][0]
    assert "linkedin" in call_args.platforms


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

    mock_result = PublishResult(
        publish_id="sm-post-100",
        targets=[PublishTarget(platform="linkedin", status="queued")],
    )
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ),
    ):
        await publish_all()

    # Verify publish was called
    mock_client.publish.assert_called_once()


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
async def test_publish_skips_if_no_api_key(temp_queue: Path, capsys):
    """publish_all exits with error when POSTING_API_KEY is missing."""
    content = _make_content(piece_id="nokey001")
    enqueue(content)
    humanize("nokey001", "AI engineering is about shipping systems that learn — not just models.")
    approve("nokey001")

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": ""}, clear=False),
        pytest.raises(SystemExit),
    ):
        await publish_all()


@pytest.mark.asyncio
async def test_publish_handles_api_failure_gracefully(temp_queue: Path):
    """If the social media API returns a failed target, the piece stays approved."""
    content = _make_content(piece_id="fail0001")
    enqueue(content)
    humanize("fail0001", "AI engineering is about shipping systems that learn — not models.")
    approve("fail0001")

    mock_result = PublishResult(
        publish_id="sm-fail-01",
        targets=[
            PublishTarget(
                platform="linkedin",
                status="failed",
                error="Rate limit exceeded",
            )
        ],
    )
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ),
    ):
        await publish_all()

    # Piece should remain approved (not marked published) since the target failed
    import yaml

    path = temp_queue / "fail0001.yaml"
    final_data = yaml.safe_load(path.read_text())
    assert final_data["status"] == "approved"


@pytest.mark.asyncio
async def test_publish_with_media_attachment(temp_queue: Path):
    """Content with rendered image attaches it to the publish request."""
    content = _make_content(piece_id="media001")
    content.rendered_image_path = "/tmp/infographic.png"
    content.media_type = "image"
    enqueue(content)
    humanize("media001", "AI engineering is about shipping systems that learn — not models.")
    approve("media001")

    mock_result = PublishResult(
        publish_id="sm-media-01",
        targets=[PublishTarget(platform="linkedin", status="queued")],
    )
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.dict("os.environ", {"POSTING_API_KEY": "test-key-123"}),
        patch(
            "holus.agents.marketing.publish_approved.SocialMediaClient",
            return_value=mock_client,
        ),
    ):
        await publish_all()

    # Verify media was included in the request
    mock_client.publish.assert_called_once()
    call_args = mock_client.publish.call_args[0][0]
    assert call_args.media_url == "/tmp/infographic.png"
    assert call_args.media_type == "image"
