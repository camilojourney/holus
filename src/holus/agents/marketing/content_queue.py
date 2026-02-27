"""Content queue for human approval before social media posting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class QueuedContent(BaseModel):
    """A piece of content waiting for approval."""

    piece_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    product: str
    platform: str
    content_type: str
    topic: str
    text: str
    reasoning: str
    generated_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending_review"  # pending_review | approved | rejected | published
    rejection_reason: str = ""


QUEUE_DIR = Path("data/content-queue")


def enqueue(content: QueuedContent) -> Path:
    """Save content to the approval queue.

    Args:
        content: Content piece to enqueue

    Returns:
        Path to the saved YAML file
    """
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / f"{content.piece_id}.yaml"

    # Convert to dict and handle datetime serialization
    data = content.model_dump()
    data["generated_at"] = content.generated_at.isoformat()

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def list_pending() -> list[QueuedContent]:
    """List all content pieces pending review.

    Returns:
        List of pending content pieces
    """
    if not QUEUE_DIR.exists():
        return []

    pending = []
    for file_path in sorted(QUEUE_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(file_path.read_text())
            if data.get("status") == "pending_review":
                # Parse datetime string back to datetime object
                if isinstance(data.get("generated_at"), str):
                    data["generated_at"] = datetime.fromisoformat(data["generated_at"])
                pending.append(QueuedContent.model_validate(data))
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            continue

    return pending


def list_approved() -> list[QueuedContent]:
    """List all content pieces approved for publishing.

    Returns:
        List of approved content pieces
    """
    if not QUEUE_DIR.exists():
        return []

    approved = []
    for file_path in sorted(QUEUE_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(file_path.read_text())
            if data.get("status") == "approved":
                if isinstance(data.get("generated_at"), str):
                    data["generated_at"] = datetime.fromisoformat(data["generated_at"])
                approved.append(QueuedContent.model_validate(data))
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            continue

    return approved


def approve(piece_id: str) -> None:
    """Approve a content piece for publishing.

    Args:
        piece_id: ID of the content piece to approve
    """
    path = QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "approved"
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def reject(piece_id: str, reason: str = "") -> None:
    """Reject a content piece.

    Args:
        piece_id: ID of the content piece to reject
        reason: Optional reason for rejection
    """
    path = QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "rejected"
    data["rejection_reason"] = reason
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def mark_published(piece_id: str, post_id: str) -> None:
    """Mark a content piece as published.

    Args:
        piece_id: ID of the content piece
        post_id: Post ID returned by Late API
    """
    path = QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = yaml.safe_load(path.read_text())
    data["status"] = "published"
    data["post_id"] = post_id
    data["published_at"] = datetime.now(tz=UTC).isoformat()
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
