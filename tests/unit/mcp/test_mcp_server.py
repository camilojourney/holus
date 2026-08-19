"""Unit tests for MCP tool functions exposed in holus.mcp.server."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
import yaml

from holus.agents.marketing import content_queue
from holus.agents.marketing.content_queue import QueuedContent
from holus.api.routes import content as content_routes
from holus.mcp import server


@pytest.fixture
def queue_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point queue storage at a temporary directory for each test."""
    temp_queue_dir = tmp_path / "content-queue"
    monkeypatch.setattr(content_queue, "QUEUE_DIR", temp_queue_dir)
    monkeypatch.setattr(server, "QUEUE_DIR", temp_queue_dir)
    return temp_queue_dir


def _make_content(
    *,
    piece_id: str = "piece-1234",
    status: str = "pending_review",
    platform: str = "linkedin",
    text: str = "Short post for review.",
    topic: str = "Queue topic",
) -> QueuedContent:
    return QueuedContent(
        piece_id=piece_id,
        product="pilaster",
        platform=platform,
        content_type="educational",
        topic=topic,
        text=text,
        reasoning="Test reasoning",
        generated_at=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
        status=status,
    )


def _read_queue_entry(queue_dir: Path, piece_id: str) -> dict[str, object]:
    path = queue_dir / f"{piece_id}.yaml"
    return yaml.safe_load(path.read_text())


def test_holus_queue_creates_piece_calls_enqueue_and_returns_metadata(queue_dir: Path):
    """holus_queue creates queued content, enqueues it, and returns queue metadata."""
    # Arrange
    text = "Launch update for LinkedIn."

    with patch("holus.mcp.server.enqueue", wraps=content_queue.enqueue) as mock_enqueue:
        # Act
        result = server.holus_queue(
            text=text,
            platform="linkedin",
            product="pilaster",
            content_type="educational",
            topic="Launch update",
        )

    # Assert
    assert result["piece_id"]
    assert result == {
        "piece_id": result["piece_id"],
        "status": "pending_review",
        "platform": "linkedin",
    }
    mock_enqueue.assert_called_once()

    saved_entry = _read_queue_entry(queue_dir, result["piece_id"])
    assert saved_entry["text"] == text
    assert saved_entry["platform"] == "linkedin"
    assert saved_entry["status"] == "pending_review"


def test_holus_list_queue_calls_list_humanizable_and_returns_expected_keys(queue_dir: Path):
    """holus_list_queue returns humanizable entries with the expected shape."""
    # Arrange
    content = _make_content(
        piece_id="piece-list",
        text="A" * 140,
        topic="List topic",
    )
    content_queue.enqueue(content)

    with patch(
        "holus.mcp.server.list_humanizable", wraps=content_queue.list_humanizable
    ) as mock_list:
        # Act
        result = server.holus_list_queue()

    # Assert
    mock_list.assert_called_once()
    assert len(result) == 1
    assert set(result[0]) == {
        "piece_id",
        "platform",
        "product",
        "status",
        "topic",
        "text_preview",
        "generated_at",
    }
    assert result[0]["piece_id"] == "piece-list"
    assert result[0]["platform"] == "linkedin"
    assert result[0]["status"] == "pending_review"
    assert result[0]["text_preview"].endswith("...")
    assert len(result[0]["text_preview"]) == 123


def test_holus_approve_humanizes_pending_humanization_and_returns_approved(queue_dir: Path):
    """holus_approve humanizes when needed, approves the piece, and returns approved."""
    # Arrange
    content = _make_content(piece_id="piece-approve", status="pending_humanization")
    content_queue.enqueue(content)

    with (
        patch("holus.mcp.server.humanize", wraps=content_queue.humanize) as mock_humanize,
        patch("holus.mcp.server.approve", wraps=content_queue.approve) as mock_approve,
    ):
        # Act
        result = server.holus_approve("piece-approve")

    # Assert
    assert result == {"piece_id": "piece-approve", "status": "approved"}
    mock_humanize.assert_called_once_with("piece-approve", content.text)
    mock_approve.assert_called_once_with("piece-approve")

    saved_entry = _read_queue_entry(queue_dir, "piece-approve")
    assert saved_entry["status"] == "approved"
    assert saved_entry["humanized_text"] == content.text


def test_holus_reject_calls_reject_and_returns_rejected(queue_dir: Path):
    """holus_reject delegates to reject() and returns rejected metadata."""
    # Arrange
    content = _make_content(piece_id="piece-reject")
    content_queue.enqueue(content)

    with patch("holus.mcp.server.reject", wraps=content_queue.reject) as mock_reject:
        # Act
        result = server.holus_reject("piece-reject", reason="Needs revision")

    # Assert
    assert result == {"piece_id": "piece-reject", "status": "rejected"}
    mock_reject.assert_called_once_with("piece-reject", "Needs revision")

    saved_entry = _read_queue_entry(queue_dir, "piece-reject")
    assert saved_entry["status"] == "rejected"
    assert saved_entry["rejection_reason"] == "Needs revision"


@pytest.mark.asyncio
async def test_holus_publish_requires_approved_piece_and_revision(
    queue_dir: Path,
):
    """MCP publishing fails closed without an immutable reviewed revision."""
    result = await server.holus_publish(
        text="Publish this update.",
        platform="linkedin",
        product="pilaster",
    )

    assert result == {"error": "APPROVAL_REQUIRED", "piece_id": None}
    assert list(queue_dir.glob("*")) == []


@pytest.mark.asyncio
async def test_p0_holus_publish_returns_contained_before_delivery_side_effects(
    queue_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Immediate MCP publish is contained after approval and before client delivery."""
    monkeypatch.setattr(content_routes, "CONTENT_QUEUE_DIR", queue_dir)
    content = _make_content(piece_id="piece-contained", status="pending_review")
    content_queue.enqueue(content)
    server.holus_approve("piece-contained")
    revision = _read_queue_entry(queue_dir, "piece-contained")["content_revision"]

    result = await server.holus_publish(
        text=content.text,
        platform="linkedin",
        product="pilaster",
        piece_id="piece-contained",
        expected_revision=str(revision),
    )

    assert result == {
        "piece_id": "piece-contained",
        "publish_id": None,
        "platform": "linkedin",
        "status": "contained",
    }
    saved_entry = _read_queue_entry(queue_dir, "piece-contained")
    assert saved_entry["status"] == "approved"
    assert "post_id" not in saved_entry


def test_holus_approve_returns_error_when_piece_not_found():
    """holus_approve returns an error payload for a missing piece."""
    # Arrange
    piece_id = "missing-piece"

    # Act
    result = server.holus_approve(piece_id)

    # Assert
    assert result == {"error": f"Content piece {piece_id} not found", "piece_id": piece_id}


def test_holus_approve_auto_humanizes_pending_review_before_approve(queue_dir: Path):
    """holus_approve humanizes pending_review content before approving it."""
    # Arrange
    content = _make_content(piece_id="piece-auto-humanize", status="pending_review")
    content_queue.enqueue(content)
    call_order: list[str] = []

    def humanize_spy(piece_id: str, humanized_text: str):
        call_order.append("humanize")
        return content_queue.humanize(piece_id, humanized_text)

    def approve_spy(piece_id: str):
        call_order.append("approve")
        return content_queue.approve(piece_id)

    with (
        patch("holus.mcp.server.humanize", side_effect=humanize_spy) as mock_humanize,
        patch("holus.mcp.server.approve", side_effect=approve_spy) as mock_approve,
    ):
        # Act
        result = server.holus_approve("piece-auto-humanize")

    # Assert
    assert result == {"piece_id": "piece-auto-humanize", "status": "approved"}
    assert call_order == ["humanize", "approve"]
    mock_humanize.assert_called_once_with("piece-auto-humanize", content.text)
    mock_approve.assert_called_once_with("piece-auto-humanize")

    saved_entry = _read_queue_entry(queue_dir, "piece-auto-humanize")
    assert saved_entry["status"] == "approved"
    assert saved_entry["humanized_text"] == content.text
