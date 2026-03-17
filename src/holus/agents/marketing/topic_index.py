"""Recently-published topic index for content deduplication.

Prevents the system from generating the same "How I built Pilaster" post
every week. Reads content-queue files and extracts topics, then provides
a similarity check and a context string for the planner prompt.

Usage::

    index = TopicIndex(queue_dir=Path("data/content-queue"))
    recent = index.recent_topics(days=30)
    # ["MCP vs SKILLS — Two Paradigms", "Why AI Agents Fail After Week 1", ...]

    is_dup = index.is_duplicate("MCP vs Skills for AI agents", threshold=0.7)
    # True — too similar to existing topic

    context = index.as_prompt_context(days=30)
    # "RECENTLY PUBLISHED (do NOT repeat these topics):\n- MCP vs SKILLS...\n- ..."
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class TopicIndex:
    """Track recently published topics to prevent content repetition."""

    def __init__(self, queue_dir: Path | str = "data/content-queue") -> None:
        self._queue_dir = Path(queue_dir)

    def recent_topics(self, days: int = 30) -> list[dict[str, str]]:
        """Return topics from the last N days with metadata.

        Returns list of {topic, format, platform, date} dicts, most recent first.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        topics: list[dict[str, str]] = []

        if not self._queue_dir.exists():
            return topics

        for path in self._queue_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                generated_at = data.get("generated_at", "")
                if generated_at and generated_at > cutoff.isoformat():
                    topic = data.get("topic", "")
                    if topic:
                        topics.append({
                            "topic": topic,
                            "format": data.get("content_type", "unknown"),
                            "platform": data.get("platform", "unknown"),
                            "date": generated_at[:10],
                            "status": data.get("status", "unknown"),
                        })
            except (json.JSONDecodeError, OSError):
                continue

        topics.sort(key=lambda t: t.get("date", ""), reverse=True)
        return topics

    def recent_topic_strings(self, days: int = 30) -> list[str]:
        """Return just the topic strings for quick comparison."""
        return [t["topic"] for t in self.recent_topics(days=days)]

    def is_duplicate(
        self,
        new_topic: str,
        *,
        days: int = 30,
        threshold: float = 0.6,
    ) -> bool:
        """Check if a new topic is too similar to a recently published one.

        Uses word overlap ratio (Jaccard similarity on lowercased words).
        Threshold 0.6 = 60% of words overlap → likely duplicate.
        """
        new_words = set(new_topic.lower().split())
        if len(new_words) < 2:
            return False

        for existing in self.recent_topic_strings(days=days):
            existing_words = set(existing.lower().split())
            if not existing_words:
                continue
            intersection = new_words & existing_words
            union = new_words | existing_words
            similarity = len(intersection) / len(union) if union else 0
            if similarity >= threshold:
                logger.info(
                    "Duplicate detected: '%s' ≈ '%s' (similarity %.2f)",
                    new_topic[:50], existing[:50], similarity,
                )
                return True

        return False

    def as_prompt_context(self, days: int = 30, max_items: int = 20) -> str:
        """Generate a context string for the planner prompt.

        Injects recently published topics so the LLM avoids repetition.
        """
        topics = self.recent_topics(days=days)[:max_items]
        if not topics:
            return ""

        lines = ["RECENTLY PUBLISHED (do NOT repeat these topics or angles):"]
        for t in topics:
            lines.append(f"- [{t['date']}] {t['topic']} ({t['format']} on {t['platform']})")

        lines.append("")
        lines.append("Create content with a DIFFERENT angle, topic, or thesis.")
        return "\n".join(lines)
