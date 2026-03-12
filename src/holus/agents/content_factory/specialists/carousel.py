"""Carousel specialist creator.

Produces carousel content suitable for LinkedIn document posts and Instagram
multi-image posts.  Best for tutorials, comparisons, and step-by-step guides.

The specialist stores the carousel as a JSON object in ``raw_content``::

    {
        "slides": [
            {"slide_number": 1, "headline": "...", "body": "...", "visual_hint": "..."},
            ...
        ],
        "cta_slide": {"slide_number": 10, "headline": "...", "body": "...", "visual_hint": ""},
        "topic_summary": "..."
    }
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..models import ContentIdea, ContentPiece, FormatType
from .base import BaseSpecialist

logger = logging.getLogger(__name__)

# Platform limits for carousel slides.
_MIN_SLIDES = 4
_MAX_SLIDES = 10
_MAX_HEADLINE_CHARS = 80
_MAX_BODY_CHARS = 200


def _build_slide(
    slide_number: int,
    headline: str,
    body: str = "",
    visual_hint: str = "",
) -> dict[str, Any]:
    """Build a single slide dict with length enforcement."""
    return {
        "slide_number": slide_number,
        "headline": headline[:_MAX_HEADLINE_CHARS],
        "body": body[:_MAX_BODY_CHARS],
        "visual_hint": visual_hint,
    }


class CarouselCreator(BaseSpecialist):
    """Creates carousel content for tutorials, comparisons, and step-by-step guides.

    Each carousel has 4-10 content slides plus a final CTA slide.
    The raw_content is a JSON string with slides + cta_slide + topic_summary.
    """

    format_type = FormatType.CAROUSEL

    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a carousel content piece.

        Args:
            idea: The content idea to create a carousel for.
            context: May contain:
                - ``claude_client``: Claude API client (``client.call(...)``).
                - ``brand``: Brand identity dict (for voice/tone).
                - ``products``: Products dict (for product context).
                - ``platform_knowledge``: Platform constraints string.

        Returns:
            A :class:`ContentPiece` with carousel JSON in ``raw_content``.
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
        """Call Claude to generate carousel slides, return JSON string."""
        brand_voice = _extract_voice(brand)
        product_context = _extract_product(products, product)

        system_prompt = (
            "You are a carousel content specialist. Create a LinkedIn/Instagram carousel "
            "with 5-8 slides on the given topic. Respond with ONLY a valid JSON object "
            "in this exact format:\n"
            '{"slides": [{"slide_number": N, "headline": "...", "body": "...", "visual_hint": "..."}], '
            '"cta_slide": {"slide_number": N, "headline": "...", "body": "...", "visual_hint": ""}, '
            '"topic_summary": "..."}\n\n'
            f"Brand voice: {brand_voice}\n"
            f"Product context: {product_context}"
        )
        user_message = f"Topic: {topic}\nContent pillar: {pillar}" + (
            f"\nNotes: {notes}" if notes else ""
        )

        try:
            response = client.call(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tier="operational",
                max_tokens=2048,
                agent_id="carousel-specialist",
            )
            response_text = response if isinstance(response, str) else str(response)
            return _validate_and_normalise(response_text, topic)
        except Exception:
            logger.exception("Claude call failed in CarouselCreator; using fallback")
            return self._build_fallback(topic)

    def _build_fallback(self, topic: str) -> str:
        """Build a minimal carousel skeleton when Claude is unavailable."""
        slides = [
            _build_slide(1, f"The problem with {topic}", "Most people don't realise this..."),
            _build_slide(2, "Why this matters", "Here's what changes when you understand it"),
            _build_slide(3, "The core insight", "The key thing to know is..."),
            _build_slide(4, "How to apply this", "Three steps to get started"),
            _build_slide(5, "Common mistake to avoid", "Don't fall into this trap"),
        ]
        cta = _build_slide(6, "Found this useful?", "Follow for more insights like this")
        payload = {
            "slides": slides,
            "cta_slide": cta,
            "topic_summary": topic[:120],
        }
        return json.dumps(payload)


def _validate_and_normalise(response_text: str, topic: str) -> str:
    """Parse and validate Claude's JSON output; return a canonical JSON string."""

    # Try direct parse first
    for attempt in (response_text, _extract_json_block(response_text)):
        if attempt is None:
            continue
        try:
            data = json.loads(attempt.strip())
        except (json.JSONDecodeError, TypeError):
            continue

        slides = data.get("slides", [])
        if not isinstance(slides, list) or len(slides) < _MIN_SLIDES:
            break  # malformed — fall through to fallback

        # Clamp field lengths
        clean_slides = [
            _build_slide(
                s.get("slide_number", i + 1),
                s.get("headline", "")[:_MAX_HEADLINE_CHARS],
                s.get("body", "")[:_MAX_BODY_CHARS],
                s.get("visual_hint", ""),
            )
            for i, s in enumerate(slides[:_MAX_SLIDES])
        ]
        cta_raw = data.get("cta_slide", {})
        cta = _build_slide(
            cta_raw.get("slide_number", len(clean_slides) + 1),
            cta_raw.get("headline", "Follow for more"),
            cta_raw.get("body", ""),
        )
        return json.dumps(
            {
                "slides": clean_slides,
                "cta_slide": cta,
                "topic_summary": str(data.get("topic_summary", topic))[:200],
            }
        )

    # Fallback: construct from lines
    lines = [ln.strip() for ln in response_text.splitlines() if ln.strip()]
    slides = [
        _build_slide(i + 1, line[:_MAX_HEADLINE_CHARS])
        for i, line in enumerate(lines[:_MAX_SLIDES])
    ]
    while len(slides) < _MIN_SLIDES:
        slides.append(_build_slide(len(slides) + 1, "..."))
    cta = _build_slide(len(slides) + 1, "Follow for more insights")
    return json.dumps({"slides": slides, "cta_slide": cta, "topic_summary": topic[:120]})


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
