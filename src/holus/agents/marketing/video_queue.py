"""Video queue for human approval before Genpeli delivery.

Mirrors content_queue.py for video content. Videos are stored as YAML files
in ``data/video-queue/`` with the same lifecycle: pending_review → approved
→ published (or rejected).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class QueuedVideo(BaseModel):
    """A processed video waiting for human approval."""

    piece_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_id: str = Field(description="Genpeli job identifier")
    preview_url: str = Field(description="URL to preview the processed video")
    product: str
    platform: str
    content_type: str
    topic: str
    reasoning: str
    decision: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialised ContentDecision that triggered the video",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending_review"  # pending_review | approved | rejected | published
    rejection_reason: str = ""


VIDEO_QUEUE_DIR = Path("data/video-queue")


def enqueue_video(video: QueuedVideo) -> Path:
    """Save a video to the approval queue.

    Args:
        video: Video piece to enqueue.

    Returns:
        Path to the saved YAML file.
    """
    VIDEO_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = VIDEO_QUEUE_DIR / f"{video.piece_id}.yaml"

    data = video.model_dump()
    data["generated_at"] = video.generated_at.isoformat()

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def _load_by_status(status: str) -> list[QueuedVideo]:
    """Load all videos with a given status from the queue directory."""
    if not VIDEO_QUEUE_DIR.exists():
        return []

    results: list[QueuedVideo] = []
    for file_path in sorted(VIDEO_QUEUE_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(file_path.read_text())
            if data.get("status") == status:
                if isinstance(data.get("generated_at"), str):
                    data["generated_at"] = datetime.fromisoformat(data["generated_at"])
                results.append(QueuedVideo.model_validate(data))
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            continue

    return results


def list_pending_videos() -> list[QueuedVideo]:
    """List all videos pending human review."""
    return _load_by_status("pending_review")


def list_approved_videos() -> list[QueuedVideo]:
    """List all videos approved for delivery."""
    return _load_by_status("approved")


def approve_video(piece_id: str) -> None:
    """Approve a video for Genpeli delivery.

    Args:
        piece_id: ID of the video piece to approve.
    """
    path = VIDEO_QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Video piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "approved"
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def reject_video(piece_id: str, reason: str = "") -> None:
    """Reject a video.

    Args:
        piece_id: ID of the video piece to reject.
        reason: Optional reason for rejection.
    """
    path = VIDEO_QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Video piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "rejected"
    data["rejection_reason"] = reason
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def mark_published(piece_id: str, post_id: str) -> None:
    """Mark a video as published to social media.

    Args:
        piece_id: ID of the video piece.
        post_id: Post ID returned by the publishing service.
    """
    path = VIDEO_QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Video piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "published"
    data["post_id"] = post_id
    data["published_at"] = datetime.now(tz=UTC).isoformat()
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
