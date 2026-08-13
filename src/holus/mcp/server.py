from __future__ import annotations

from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from holus.agents.marketing.content_queue import (
    QUEUE_DIR,
    QueuedContent,
    approve,
    enqueue,
    humanize,
    list_humanizable,
    reject,
)

# Configuration and Environment Validation
mcp = FastMCP("holus")


def _load_queue_entry(piece_id: str) -> dict[str, Any]:
    """Helper to load a raw queue entry for status checks."""
    path = QUEUE_DIR / f"{piece_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Content piece {piece_id} not found")

    loaded = yaml.safe_load(path.read_text())
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid queue entry for {piece_id}")

    return dict(loaded)


def _preview_text(text: str) -> str:
    """Truncate text for preview in list views."""
    if len(text) <= 120:
        return text
    return f"{text[:120]}..."


@mcp.tool()
def holus_queue(
    text: str,
    platform: str,
    product: str = "openclaw",
    content_type: str = "educational",
    topic: str = "",
) -> dict[str, str]:
    """Enqueue a piece of content for human review and humanization.

    Args:
        text: The content text to be reviewed.
        platform: Target social media platform (twitter, linkedin, etc.).
        product: Related product (default: openclaw).
        content_type: Type of content (educational, marketing, etc.).
        topic: Specific topic of the content.
    """
    try:
        content = QueuedContent(
            product=product,
            platform=platform,
            content_type=content_type,
            topic=topic,
            text=text,
            reasoning="Enqueued via MCP tool",
        )
        enqueue(content)
        return {
            "piece_id": content.piece_id,
            "status": content.status,
            "platform": content.platform,
        }
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def holus_list_queue() -> list[dict[str, Any]]:
    """List all content pieces pending human review or humanization."""
    try:
        items = list_humanizable()
        return [
            {
                "piece_id": item.piece_id,
                "platform": item.platform,
                "product": item.product,
                "status": item.status,
                "topic": item.topic,
                "text_preview": _preview_text(item.text),
                "generated_at": item.generated_at.isoformat(),
            }
            for item in items
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


@mcp.tool()
def holus_approve(piece_id: str, text: str | None = None) -> dict[str, str]:
    """Approve a content piece for publishing.

    If the piece is pending review/humanization, it will be automatically
    humanized. If 'text' is provided, it will be used as the humanized version.

    Args:
        piece_id: The ID of the content piece to approve.
        text: Optional human-edited text. If omitted, original text is used.
    """
    try:
        data = _load_queue_entry(piece_id)
        status = data.get("status")

        if status == "approved":
            return {"piece_id": piece_id, "status": "approved", "note": "Already approved"}

        if status == "published":
            return {"piece_id": piece_id, "status": "published", "note": "Already published"}

        # SPEC-032: Apply humanization if pending
        if status in ("pending_review", "pending_humanization"):
            final_text = text if text is not None else data.get("text")
            if not isinstance(final_text, str):
                raise ValueError(f"Queue entry {piece_id} is missing text")
            humanize(piece_id, final_text)

        approve(piece_id)
    except Exception as exc:
        return {"error": str(exc), "piece_id": piece_id}

    return {"piece_id": piece_id, "status": "approved"}


@mcp.tool()
def holus_reject(piece_id: str, reason: str = "") -> dict[str, str]:
    """Reject a content piece with an optional reason.

    Args:
        piece_id: The ID of the content piece to reject.
        reason: Optional explanation for rejection.
    """
    try:
        data = _load_queue_entry(piece_id)
        if data.get("status") == "rejected":
            return {"piece_id": piece_id, "status": "rejected", "note": "Already rejected"}

        reject(piece_id, reason)
    except Exception as exc:
        return {"error": str(exc), "piece_id": piece_id}

    return {"piece_id": piece_id, "status": "rejected"}


@mcp.tool()
async def holus_publish(
    text: str,
    platform: str,
    product: str = "openclaw",
    media_url: str | None = None,
    media_type: str | None = None,
    piece_id: str | None = None,
    expected_revision: str | None = None,
) -> dict[str, Any]:
    """Publish an already human-approved queue piece through the guarded API.

    Args:
        text: The final text to publish.
        platform: Target platform (twitter, linkedin, etc.).
        product: Related product.
        media_url: Optional URL to an image or video.
        media_type: 'image' or 'video'.
        piece_id: Approved queue piece to publish.
        expected_revision: Exact immutable approved content revision.
    """
    if not piece_id or not expected_revision:
        return {"error": "APPROVAL_REQUIRED", "piece_id": piece_id}
    try:
        from holus.api.models import ContentPublishRequest
        from holus.api.routes.content import _find_content_raw, publish_content

        _, raw = _find_content_raw(piece_id)
        if raw.get("text") != text or raw.get("platform") != platform:
            return {"error": "REVISION_CONFLICT", "piece_id": piece_id}
        response = await publish_content(
            piece_id,
            ContentPublishRequest(expected_revision=expected_revision),
        )
        return {
            "piece_id": piece_id,
            "publish_id": response.publish_id,
            "platform": platform,
            "status": response.status,
        }
    except Exception as exc:
        return {"error": str(exc), "piece_id": piece_id}


if __name__ == "__main__":
    mcp.run()
