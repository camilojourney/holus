"""Video brief specialist creator.

Produces a video brief for genpeli (the video editing pipeline). This specialist
does NOT create a video — it creates the structured brief that gets sent to
genpeli as the ``instruction`` field.

The brief is designed so genpeli can:
- Know the talking points (key_points list)
- Know the tone and duration target
- Have a script outline to guide editing
- Know what to show on screen (visual_references)

The raw_content JSON schema::

    {
        "title": "...",
        "key_points": ["...", "...", ...],
        "tone": "technical walkthrough | casual explainer | ...",
        "duration_target_seconds": 60,
        "visual_references": ["What to show on screen", ...],
        "script_outline": "Rough script or talking points",
        "music_mood": "none | ambient | upbeat | dramatic"
    }

Target platforms: Instagram (Reels), Threads, LinkedIn, Facebook.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..models import ContentIdea, ContentPiece, FormatType
from .base import BaseSpecialist

logger = logging.getLogger(__name__)

_VALID_MOODS = frozenset({"none", "ambient", "upbeat", "dramatic"})


class VideoBriefCreator(BaseSpecialist):
    """Creates a structured video brief for genpeli.

    The brief contains talking points, tone, duration target, and visual cues.
    Holus sends this brief to genpeli via REST API — genpeli handles the
    actual editing, captioning, and delivery.
    """

    format_type = FormatType.VIDEO_BRIEF

    # Video briefs require higher quality — the production cost is higher.
    quality_threshold = 75

    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a video brief content piece.

        Args:
            idea: The content idea to create a video brief for.
            context: May contain:
                - ``claude_client``: Claude API client.
                - ``brand``: Brand identity dict.
                - ``products``: Products dict.
                - ``duration_target``: Desired duration in seconds (default 60).

        Returns:
            A :class:`ContentPiece` with video brief JSON in ``raw_content``.
        """
        topic = idea.topic
        product = idea.product
        pillar = idea.content_pillar
        notes = idea.notes
        duration = int(context.get("duration_target", 60))

        claude_client = context.get("claude_client")
        brand = context.get("brand", {})
        products = context.get("products", {})

        if claude_client is not None:
            raw = await self._call_claude(
                claude_client, topic, product, pillar, notes, brand, products, duration
            )
        else:
            raw = self._build_fallback(topic, duration)

        return self._make_piece(idea=idea, raw_content=raw, model_used="sonnet")

    async def _call_claude(
        self,
        client: Any,
        topic: str,
        product: str,
        pillar: str,
        notes: str,
        brand: dict[str, Any],
        products: dict[str, Any],
        duration: int,
    ) -> str:
        """Call Claude to generate a video brief; return JSON string."""
        product_ctx = _extract_product(products, product)
        voice = _extract_voice(brand)

        system_prompt = (
            "You are a video brief specialist. Create a structured brief for a short-form "
            f"video ({duration}s target) on the given topic. Respond with ONLY a valid JSON "
            "object in this exact format:\n"
            '{"title": "...", "key_points": ["...", "..."], "tone": "...", '
            f'"duration_target_seconds": {duration}, '
            '"visual_references": ["..."], "script_outline": "...", "music_mood": "none"}\n\n'
            "key_points: 2-7 talking points\n"
            "tone: e.g. casual explainer, technical walkthrough, inspirational\n"
            "music_mood: none | ambient | upbeat | dramatic\n"
            f"Brand voice: {voice}\nProduct context: {product_ctx}"
        )
        user_message = f"Topic: {topic}\nContent pillar: {pillar}" + (
            f"\nNotes: {notes}" if notes else ""
        )

        try:
            response = client.call(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tier="operational",
                max_tokens=1500,
                agent_id="video-brief-specialist",
            )
            text = response if isinstance(response, str) else str(response)
            return _parse_video_brief_response(text, topic, duration)
        except Exception:
            logger.exception("Claude call failed in VideoBriefCreator; using fallback")
            return self._build_fallback(topic, duration)

    def _build_fallback(self, topic: str, duration: int = 60) -> str:
        """Construct a minimal video brief skeleton."""
        return json.dumps(
            {
                "title": topic[:100],
                "key_points": [
                    f"Why {topic} matters",
                    "The core insight",
                    "How to apply it",
                ],
                "tone": "casual explainer",
                "duration_target_seconds": max(15, min(duration, 180)),
                "visual_references": ["Screen recording of the tool", "Code walkthrough"],
                "script_outline": (
                    f"Open with the problem. Explain {topic}. "
                    "Show a concrete example. Close with a takeaway."
                ),
                "music_mood": "none",
            }
        )


def _parse_video_brief_response(text: str, topic: str, duration: int) -> str:
    """Parse Claude's JSON output into a canonical video brief JSON string."""

    for raw in (text, _extract_json_block(text)):
        if not raw:
            continue
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue

        key_points = data.get("key_points", [])
        if not isinstance(key_points, list):
            key_points = []
        if len(key_points) < 2:
            key_points.extend(["Key point"] * (2 - len(key_points)))
        key_points = [str(p)[:200] for p in key_points[:7]]

        mood = str(data.get("music_mood", "none")).lower()
        if mood not in _VALID_MOODS:
            mood = "none"

        dur = int(data.get("duration_target_seconds", duration))
        dur = max(15, min(dur, 180))

        return json.dumps(
            {
                "title": str(data.get("title", topic))[:200],
                "key_points": key_points,
                "tone": str(data.get("tone", "casual explainer"))[:100],
                "duration_target_seconds": dur,
                "visual_references": [str(v)[:200] for v in data.get("visual_references", [])[:10]],
                "script_outline": str(data.get("script_outline", ""))[:3000],
                "music_mood": mood,
            }
        )

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:100] if lines else topic
    key_points = lines[1:8] if len(lines) > 1 else ["Key point 1", "Key point 2"]
    if len(key_points) < 2:
        key_points.extend(["Key point"] * (2 - len(key_points)))

    return json.dumps(
        {
            "title": title,
            "key_points": key_points[:7],
            "tone": "casual explainer",
            "duration_target_seconds": max(15, min(duration, 180)),
            "visual_references": [],
            "script_outline": text[:1000],
            "music_mood": "none",
        }
    )


def _extract_json_block(text: str) -> str | None:
    import re

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else None


def _extract_voice(brand: dict[str, Any]) -> str:
    try:
        voice = brand.get("voice", {})
        archetype = voice.get("archetype", "")
        tone = voice.get("tone", [])
        tone_str = ", ".join(tone[:3]) if isinstance(tone, list) else str(tone)
        return f"{archetype} — {tone_str}" if archetype else tone_str
    except Exception:
        return "professional, direct, evidence-based"


def _extract_product(products: dict[str, Any], product_key: str) -> str:
    try:
        plist = products.get("products", products)
        info = plist.get(product_key, {})
        name = info.get("name", product_key)
        tagline = info.get("tagline", "")
        return f"{name}: {tagline}" if tagline else name
    except Exception:
        return ""
