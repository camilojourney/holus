"""Automated content publishing gate based on judge scores.

Reads pending_review content from the queue, routes based on judge verdict:
- PASS (score >= 0.8) + brand-safety PASS → auto-approve + publish
- PARTIAL (0.5-0.8) → leave for human review, send Telegram notification
- FAIL (< 0.5) → auto-reject, trigger reflexion on the failure

This replaces the fully manual review flow for high-confidence content
while keeping human oversight for borderline pieces.

Usage::

    from holus.agents.marketing.auto_publish import process_queue
    results = await process_queue()
    # [{"piece_id": "abc", "action": "published", "score": 0.85}, ...]
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

QUEUE_DIR = Path("data/content-queue")

# Thresholds from engineering consultation verdict
PASS_THRESHOLD = 0.8
PARTIAL_THRESHOLD = 0.5


def _load_pending_with_scores() -> list[dict[str, Any]]:
    """Load all pending_review items that have judge scores."""
    if not QUEUE_DIR.exists():
        return []

    items: list[dict[str, Any]] = []
    # Check both .yaml and .json files
    for pattern in ("*.yaml", "*.json"):
        for path in sorted(QUEUE_DIR.glob(pattern)):
            try:
                text = path.read_text(encoding="utf-8")
                data = yaml.safe_load(text) if pattern == "*.yaml" else json.loads(text)

                if not isinstance(data, dict):
                    continue
                if data.get("status") != "pending_review":
                    continue

                data["_file_path"] = str(path)
                items.append(data)
            except Exception:
                continue

    return items


def _get_judge_score(item: dict[str, Any]) -> float | None:
    """Extract judge score from queue item (may be in different locations)."""
    # Direct field
    if isinstance(item.get("judge_score"), (int, float)):
        return float(item["judge_score"])

    # Nested in quality dict
    quality = item.get("quality", {})
    if isinstance(quality.get("judge_score"), (int, float)):
        return float(quality["judge_score"])

    return None


def _get_judge_verdict(item: dict[str, Any]) -> str | None:
    """Extract judge verdict from queue item."""
    return item.get("judge_verdict") or item.get("quality", {}).get("judge_verdict")


def _update_item(file_path: str, updates: dict[str, Any]) -> None:
    """Update a queue item file with new fields."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    if path.suffix == ".yaml":
        data = yaml.safe_load(text) or {}
        data.update(updates)
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        data = json.loads(text)
        data.update(updates)
        path.write_text(json.dumps(data, indent=2))


async def _publish_piece(item: dict[str, Any]) -> str | None:
    """Publish a piece via social-media MCP. Returns publish_id or None."""
    try:
        from holus.integrations.social_media import PublishRequest, SocialMediaClient

        client = SocialMediaClient()
        request = PublishRequest(
            text=item.get("text", ""),
            platform=item.get("platform", "linkedin"),
            media_urls=[],
        )

        # Add PDF/image attachment if available
        pdf_path = item.get("pdf_path") or item.get("rendered_pdf_path")
        image_path = item.get("rendered_image_path")
        if pdf_path:
            request.media_urls = [pdf_path]
        elif image_path:
            request.media_urls = [image_path]

        result = await client.publish(request)
        return result.post_id if result and result.post_id else None

    except Exception as exc:
        logger.error("Publish failed for %s: %s", item.get("piece_id", "?"), exc)
        return None


def _send_telegram_notification(item: dict[str, Any], action: str, score: float) -> None:
    """Send Telegram notification for PARTIAL items needing review."""
    try:
        import requests

        bot_token = ""  # Will be loaded from env
        chat_id = ""
        import os

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not bot_token or not chat_id:
            logger.debug("Telegram not configured; skipping notification")
            return

        topic = item.get("topic", "Unknown")[:80]
        platform = item.get("platform", "?")
        piece_id = item.get("piece_id", "?")
        feedback = item.get("judge_feedback", "")[:200]

        if action == "needs_review":
            text = (
                f"📋 Content needs review\n"
                f"Score: {score:.2f} (PARTIAL)\n"
                f"Topic: {topic}\n"
                f"Platform: {platform}\n"
                f"ID: {piece_id}\n"
                f"Feedback: {feedback}"
            )
        elif action == "auto_published":
            text = f"✅ Auto-published (score {score:.2f})\n{topic} on {platform}"
        elif action == "auto_rejected":
            text = f"❌ Auto-rejected (score {score:.2f})\n{topic}\nReason: {feedback}"
        else:
            return

        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        logger.debug("Telegram notification failed: %s", exc)


def _trigger_reflexion(item: dict[str, Any], score: float) -> None:
    """Generate and store a reflection for rejected content.

    Uses judge feedback to create a structured reflection, then stores it
    in trajectory for future retrieval during content generation.
    """
    try:
        from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

        feedback = item.get("judge_feedback", "No specific feedback")
        topic = item.get("topic", "Unknown topic")[:100]
        fmt = item.get("content_type", item.get("format", "unknown"))
        platform = item.get("platform", "unknown")

        reflection = (
            f"REJECTED ({score:.2f}): {fmt} for {platform} — '{topic}'. "
            f"Judge feedback: {feedback}. "
            f"Next time: address this specific issue before generating."
        )

        tl = TrajectoryLogger(Path(".self-improvement/memory/trajectory.jsonl"))
        tl.append(TrajectoryEntry(
            agent_id="auto-publish",
            task_type="reflexion",
            task_summary=f"Reflection on rejected {fmt}: {topic}",
            status="success",
            judge_score=score,
            judge_verdict="FAIL",
            judge_feedback=reflection,
            metadata={
                "schema_version": 2,
                "failure_class": "quality_issue",
                "platform": platform,
                "content_type": fmt,
                "original_feedback": feedback,
            },
        ))

        logger.info("Reflexion stored for rejected piece: %s", topic[:50])

    except Exception as exc:
        logger.debug("Reflexion storage failed (non-blocking): %s", exc)


async def process_queue(*, dry_run: bool = False) -> list[dict[str, Any]]:
    """Process all pending_review items based on judge scores.

    Returns list of actions taken: {piece_id, action, score, reason}.
    """
    items = _load_pending_with_scores()
    results: list[dict[str, Any]] = []

    for item in items:
        piece_id = item.get("piece_id", Path(item["_file_path"]).stem)
        score = _get_judge_score(item)
        verdict = _get_judge_verdict(item)
        file_path = item["_file_path"]

        # No judge score → skip (leave for manual review)
        if score is None:
            results.append({
                "piece_id": piece_id,
                "action": "skipped",
                "reason": "no judge score",
            })
            continue

        if score >= PASS_THRESHOLD and verdict != "FAIL":
            # AUTO-PUBLISH: high confidence + no safety flags
            if dry_run:
                action = "would_publish"
                publish_id = None
            else:
                publish_id = await _publish_piece(item)
                if publish_id:
                    _update_item(file_path, {
                        "status": "published",
                        "post_id": publish_id,
                        "published_at": datetime.now(tz=UTC).isoformat(),
                        "auto_published": True,
                    })
                    action = "published"
                    _send_telegram_notification(item, "auto_published", score)
                else:
                    action = "publish_failed"

            results.append({
                "piece_id": piece_id,
                "action": action,
                "score": score,
                "publish_id": publish_id if not dry_run else None,
            })

        elif score >= PARTIAL_THRESHOLD:
            # PARTIAL: needs human review
            _send_telegram_notification(item, "needs_review", score)
            results.append({
                "piece_id": piece_id,
                "action": "needs_review",
                "score": score,
                "reason": item.get("judge_feedback", "")[:200],
            })

        else:
            # FAIL: auto-reject
            if not dry_run:
                _update_item(file_path, {
                    "status": "rejected",
                    "rejection_reason": f"Auto-rejected: judge score {score:.2f} < {PARTIAL_THRESHOLD}",
                    "rejected_at": datetime.now(tz=UTC).isoformat(),
                    "auto_rejected": True,
                })
                _send_telegram_notification(item, "auto_rejected", score)
                # Reflexion: learn from the failure
                _trigger_reflexion(item, score)

            results.append({
                "piece_id": piece_id,
                "action": "rejected" if not dry_run else "would_reject",
                "score": score,
                "reason": item.get("judge_feedback", "")[:200],
            })

    logger.info(
        "Auto-publish processed %d items: %s",
        len(results),
        {r["action"] for r in results},
    )
    return results
