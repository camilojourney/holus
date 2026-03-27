"""Content queue for human approval before social media posting.

SPEC-032: Adds humanization gate between quality judge and publishing.
Status machine: pending_review → pending_humanization → humanized → approved → published
                                                                  → expired (72h)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# Valid status transitions (SPEC-032 state machine)
VALID_STATUSES = {
    "pending_review",
    "pending_humanization",
    "humanized",
    "approved",
    "rejected",
    "published",
    "expired",
}

# Maximum edit distance (Levenshtein ratio) for humanization — SPEC-032 sec requirement
MAX_EDIT_DISTANCE = 0.40

# Hours before un-humanized content expires — SPEC-032 perf requirement
EXPIRY_HOURS = 72


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
    status: str = "pending_review"
    rejection_reason: str = ""
    rendered_image_path: str | None = None
    rendered_pdf_path: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    # SPEC-032: Humanization fields
    humanized_text: str | None = None
    humanized_at: datetime | None = None
    edit_distance: float | None = None


QUEUE_DIR = Path("data/content-queue")


def _iter_queue_files(queue_dir: Path | None = None) -> list[Path]:
    """Return sorted queue files (.yaml and .json) from the content queue directory."""
    d = queue_dir or QUEUE_DIR
    if not d.exists():
        return []
    files = list(d.glob("*.yaml")) + list(d.glob("*.json"))
    return sorted(files)


def _load_queue_file(path: Path) -> dict[str, Any] | None:
    """Load a single queue file (YAML or JSON) and return its data dict, or None on error."""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _find_piece_file(piece_id: str) -> Path | None:
    """Find the queue file for a given piece_id (checks both .yaml and .json)."""
    yaml_path = QUEUE_DIR / f"{piece_id}.yaml"
    if yaml_path.exists():
        return yaml_path
    json_path = QUEUE_DIR / f"{piece_id}.json"
    if json_path.exists():
        return json_path
    # Fallback: scan files for matching piece_id field
    for path in _iter_queue_files():
        data = _load_queue_file(path)
        if data and data.get("piece_id") == piece_id:
            return path
    return None


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
    for file_path in _iter_queue_files():
        try:
            data = _load_queue_file(file_path)
            if data is None:
                continue
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
    for file_path in _iter_queue_files():
        try:
            data = _load_queue_file(file_path)
            if data is None:
                continue
            if data.get("status") == "approved":
                if isinstance(data.get("generated_at"), str):
                    data["generated_at"] = datetime.fromisoformat(data["generated_at"])
                approved.append(QueuedContent.model_validate(data))
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            continue

    return approved


def humanize(piece_id: str, humanized_text: str) -> QueuedContent:
    """Apply human edits to content. SPEC-032 humanization gate.

    Args:
        piece_id: ID of the content piece
        humanized_text: Human-edited version of the text

    Returns:
        Updated QueuedContent

    Raises:
        FileNotFoundError: If piece doesn't exist
        ValueError: If status is wrong or edit distance exceeds limit
    """
    path = _find_piece_file(piece_id)
    if path is None:
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = _load_queue_file(path)
    if data is None:
        raise FileNotFoundError(f"Content piece {piece_id} could not be loaded")

    if data["status"] not in ("pending_review", "pending_humanization"):
        raise ValueError(
            f"Cannot humanize content in status '{data['status']}'. "
            f"Must be 'pending_review' or 'pending_humanization'."
        )

    # Compute edit distance (Levenshtein ratio)
    distance = _levenshtein_ratio(data["text"], humanized_text)
    if distance > MAX_EDIT_DISTANCE:
        raise ValueError(
            f"Edit distance {distance:.1%} exceeds {MAX_EDIT_DISTANCE:.0%} limit. "
            f"This is a rewrite, not a humanization. Keep closer to the original."
        )

    data["humanized_text"] = humanized_text
    data["humanized_at"] = datetime.now(tz=UTC).isoformat()
    data["edit_distance"] = round(distance, 4)
    data["status"] = "humanized"

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    if isinstance(data.get("generated_at"), str):
        data["generated_at"] = datetime.fromisoformat(data["generated_at"])
    if isinstance(data.get("humanized_at"), str):
        data["humanized_at"] = datetime.fromisoformat(data["humanized_at"])
    return QueuedContent.model_validate(data)


def approve(piece_id: str) -> None:
    """Approve a content piece for publishing. SPEC-032: must be humanized first.

    Args:
        piece_id: ID of the content piece to approve

    Raises:
        FileNotFoundError: If piece doesn't exist
        ValueError: If content hasn't been humanized
    """
    path = _find_piece_file(piece_id)
    if path is None:
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = _load_queue_file(path)
    if data is None:
        raise FileNotFoundError(f"Content piece {piece_id} could not be loaded")

    # SPEC-032: Only humanized content can be approved
    if data["status"] != "humanized":
        raise ValueError(
            f"Cannot approve content in status '{data['status']}'. "
            f"Content must be humanized first (status='humanized')."
        )

    data["status"] = "approved"
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def reject(piece_id: str, reason: str = "") -> None:
    """Reject a content piece.

    Args:
        piece_id: ID of the content piece to reject
        reason: Optional reason for rejection
    """
    path = _find_piece_file(piece_id)
    if path is None:
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = _load_queue_file(path)
    if data is None:
        raise FileNotFoundError(f"Content piece {piece_id} could not be loaded")

    data["status"] = "rejected"
    data["rejection_reason"] = reason
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def mark_published(piece_id: str, post_id: str) -> None:
    """Mark a content piece as published.

    Args:
        piece_id: ID of the content piece
        post_id: Post ID returned by the social-media API
    """
    path = _find_piece_file(piece_id)
    if path is None:
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    data = _load_queue_file(path)
    if data is None:
        raise FileNotFoundError(f"Content piece {piece_id} could not be loaded")

    data["status"] = "published"
    data["post_id"] = post_id
    data["published_at"] = datetime.now(tz=UTC).isoformat()
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def expire_stale() -> list[str]:
    """Expire content that's been pending humanization for > 72 hours. SPEC-032.

    Returns:
        List of piece_ids that were expired.
    """
    if not QUEUE_DIR.exists():
        return []

    cutoff = datetime.now(tz=UTC) - timedelta(hours=EXPIRY_HOURS)
    expired_ids = []

    for file_path in _iter_queue_files():
        try:
            data = _load_queue_file(file_path)
            if data is None:
                continue
            if data.get("status") not in ("pending_review", "pending_humanization"):
                continue
            generated = data.get("generated_at", "")
            if isinstance(generated, str):
                generated = datetime.fromisoformat(generated)
            if not generated.tzinfo:
                generated = generated.replace(tzinfo=UTC)
            if generated < cutoff:
                data["status"] = "expired"
                file_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
                expired_ids.append(data.get("piece_id", file_path.stem))
        except Exception:
            continue

    return expired_ids


def list_humanizable() -> list[QueuedContent]:
    """List content pieces ready for humanization (pending_review or pending_humanization).

    Returns:
        List of content pieces awaiting human edit.
    """
    if not QUEUE_DIR.exists():
        return []

    items = []
    for file_path in _iter_queue_files():
        try:
            data = _load_queue_file(file_path)
            if data is None:
                continue
            if data.get("status") in ("pending_review", "pending_humanization"):
                if isinstance(data.get("generated_at"), str):
                    data["generated_at"] = datetime.fromisoformat(data["generated_at"])
                items.append(QueuedContent.model_validate(data))
        except Exception:
            continue
    return items


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Compute Levenshtein edit distance ratio between two strings.

    Returns a float 0.0 (identical) to 1.0 (completely different).
    """
    if s1 == s2:
        return 0.0
    len1, len2 = len(s1), len(s2)
    if not len1 or not len2:
        return 1.0

    # Optimized single-row DP
    prev = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr = [i] + [0] * len2
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr

    distance = prev[len2]
    return distance / max(len1, len2)
