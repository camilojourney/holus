"""Text specialist creator.

Produces text post content — the default and most versatile format.
Suitable for LinkedIn posts, Twitter/X threads, Threads posts, Facebook posts,
and Instagram captions (with a visual_hint for required media).

The raw_content JSON schema::

    {
        "text": "Full post text",
        "hook": "Opening line (first sentence or two)",
        "hashtags": ["tag1", "tag2"],
        "word_count": 120
    }
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..models import ContentIdea, ContentPiece, FormatType
from .base import BaseSpecialist

logger = logging.getLogger(__name__)

_MAX_HASHTAGS = 10


class TextCreator(BaseSpecialist):
    """Creates text post content for any platform.

    This is the fallback specialist — used when no other format fits the idea.
    Produces concise, hook-driven posts with optional hashtags.
    """

    format_type = FormatType.TEXT

    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a text content piece.

        Args:
            idea: The content idea to create a text post for.
            context: May contain:
                - ``claude_client``: Claude API client.
                - ``brand``: Brand identity dict.
                - ``products``: Products dict.

        Returns:
            A :class:`ContentPiece` with text JSON in ``raw_content``.
        """
        topic = idea.topic
        product = idea.product
        pillar = idea.content_pillar
        notes = idea.notes

        claude_client = context.get("claude_client")
        brand = context.get("brand", {})
        products = context.get("products", {})

        if claude_client is not None:
            raw = await self._call_claude(
                claude_client, topic, product, pillar, notes, brand, products
            )
        else:
            raw = self._build_fallback(topic)

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
    ) -> str:
        """Call Claude to generate the post text, return JSON string."""
        brand_voice = _extract_voice(brand)
        product_context = _extract_product(products, product)

        system_prompt = (
            "You are a text post content specialist. Write a compelling social media post "
            "on the given topic. Respond with ONLY a valid JSON object in this exact format:\n"
            '{"text": "Full post text", "hook": "Opening line", "hashtags": ["tag1"], '
            '"word_count": N}\n\n'
            f"Brand voice: {brand_voice}\n"
            f"Product context: {product_context}\n"
            "Keep the post under 3000 characters. Use a strong hook. No generic openers."
        )
        user_message = f"Topic: {topic}\nContent pillar: {pillar}" + (
            f"\nNotes: {notes}" if notes else ""
        )

        try:
            response = client.call(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tier="operational",
                max_tokens=1024,
                agent_id="text-specialist",
            )
            response_text = response if isinstance(response, str) else str(response)
            return _validate_and_normalise(response_text, topic)
        except Exception:
            logger.exception("Claude call failed in TextCreator; using fallback")
            return self._build_fallback(topic)

    def _build_fallback(self, topic: str) -> str:
        """Build a minimal text post skeleton when Claude is unavailable."""
        text = (
            f"Here's what I learned about {topic}.\n\n"
            "The key insight is that most people overcomplicate this.\n\n"
            "Three things that actually matter:\n"
            "1. Start with the problem, not the solution\n"
            "2. Measure what you're trying to change\n"
            "3. Iterate faster than you think you should\n\n"
            "What's your experience with this?"
        )
        hook = f"Here's what I learned about {topic}."
        payload = {
            "text": text,
            "hook": hook,
            "hashtags": [],
            "word_count": len(text.split()),
        }
        return json.dumps(payload)


def _validate_and_normalise(response_text: str, topic: str) -> str:
    """Parse and validate Claude's JSON output; return a canonical JSON string."""

    for attempt in (response_text, _extract_json_block(response_text)):
        if attempt is None:
            continue
        try:
            data = json.loads(attempt.strip())
        except (json.JSONDecodeError, TypeError):
            continue

        text = str(data.get("text", "")).strip()
        if not text:
            continue

        hook = str(data.get("hook", "")).strip()
        if not hook:
            # Extract first sentence as hook
            first_sent = text.split(".")[0].strip()
            hook = first_sent if first_sent else text[:100]

        hashtags = data.get("hashtags", [])
        if not isinstance(hashtags, list):
            hashtags = []
        hashtags = [str(h).lstrip("#") for h in hashtags[:_MAX_HASHTAGS]]

        word_count = len(text.split())

        return json.dumps(
            {
                "text": text,
                "hook": hook,
                "hashtags": hashtags,
                "word_count": word_count,
            }
        )

    # Fallback: treat raw response as the post text
    text = response_text.strip()[:3000]
    hook = text.split(".")[0].strip() if "." in text else text[:100]
    return json.dumps(
        {
            "text": text,
            "hook": hook,
            "hashtags": [],
            "word_count": len(text.split()),
        }
    )


def _extract_json_block(text: str) -> str | None:
    """Extract a ```json ... ``` or bare { ... } block from text."""
    import re

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else None


def _extract_voice(brand: dict[str, Any]) -> str:
    """Extract a concise brand voice string from brand dict."""
    try:
        voice = brand.get("voice", {})
        archetype = voice.get("archetype", "")
        tone = voice.get("tone", [])
        tone_str = ", ".join(tone[:3]) if isinstance(tone, list) else str(tone)
        return f"{archetype} — {tone_str}" if archetype else tone_str
    except Exception:
        return "professional, direct, evidence-based"


def _extract_product(products: dict[str, Any], product_key: str) -> str:
    """Extract a one-line product description for context."""
    try:
        plist = products.get("products", products)
        info = plist.get(product_key, {})
        name = info.get("name", product_key)
        tagline = info.get("tagline", "")
        return f"{name}: {tagline}" if tagline else name
    except Exception:
        return ""
