"""PDF specialist creator.

Produces PDF brief content for whitepapers, case studies, and detailed guides.
The raw_content is a JSON string with title, subtitle, sections, key_takeaway,
and estimated_pages.

Suitable for:
- LinkedIn document posts (PDF carousel)
- Gated content landing pages
- Detailed technical guides with 2-12 sections
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..models import ContentIdea, ContentPiece, FormatType
from .base import BaseSpecialist

logger = logging.getLogger(__name__)

_MIN_SECTIONS = 2
_MAX_SECTIONS = 12


class PDFCreator(BaseSpecialist):
    """Creates PDF brief content for long-form, detailed guides.

    The raw_content JSON schema::

        {
            "title": "...",
            "subtitle": "...",
            "sections": [
                {"heading": "...", "body_markdown": "...", "callout": "..." | null},
                ...
            ],
            "key_takeaway": "...",
            "estimated_pages": N
        }
    """

    format_type = FormatType.PDF

    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a PDF brief content piece.

        Args:
            idea: The content idea to create a PDF brief for.
            context: May contain:
                - ``claude_client``: Claude API client.
                - ``brand``: Brand identity dict.
                - ``products``: Products dict.

        Returns:
            A :class:`ContentPiece` with PDF brief JSON in ``raw_content``.
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
        """Call Claude to generate PDF sections; return JSON string."""
        product_ctx = _extract_product(products, product)
        voice = _extract_voice(brand)

        system_prompt = (
            "You are a PDF/whitepaper content specialist. Create a detailed content brief "
            "with 3-6 sections on the given topic. Respond with ONLY a valid JSON object "
            "in this exact format:\n"
            '{"title": "...", "subtitle": "...", '
            '"sections": [{"heading": "...", "body_markdown": "...", "callout": null}], '
            '"key_takeaway": "...", "estimated_pages": N}\n\n'
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
                max_tokens=3000,
                agent_id="pdf-specialist",
            )
            text = response if isinstance(response, str) else str(response)
            return _parse_pdf_response(text, topic)
        except Exception:
            logger.exception("Claude call failed in PDFCreator; using fallback")
            return self._build_fallback(topic)

    def _build_fallback(self, topic: str) -> str:
        """Construct a minimal PDF brief skeleton."""
        sections = [
            {
                "heading": "Introduction",
                "body_markdown": f"An overview of {topic} and why it matters.",
                "callout": None,
            },
            {
                "heading": "Core Concepts",
                "body_markdown": "The foundational ideas you need to understand.",
                "callout": None,
            },
            {
                "heading": "Practical Applications",
                "body_markdown": "How to apply these concepts in real projects.",
                "callout": "Key insight: Start small, iterate fast.",
            },
            {
                "heading": "Next Steps",
                "body_markdown": "What to do with this knowledge.",
                "callout": None,
            },
        ]
        return json.dumps(
            {
                "title": topic[:100],
                "subtitle": "",
                "sections": sections,
                "key_takeaway": f"A practical guide to {topic}.",
                "estimated_pages": 3,
            }
        )


def _parse_pdf_response(text: str, topic: str) -> str:
    """Parse Claude's JSON output into a canonical PDF JSON string."""

    for raw in (text, _extract_json_block(text)):
        if not raw:
            continue
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue

        sections = data.get("sections", [])
        if not isinstance(sections, list) or len(sections) < _MIN_SECTIONS:
            break

        clean_sections = [
            {
                "heading": str(s.get("heading", f"Section {i + 1}"))[:200],
                "body_markdown": str(s.get("body_markdown", ""))[:5000],
                "callout": s.get("callout"),
            }
            for i, s in enumerate(sections[:_MAX_SECTIONS])
        ]
        est = max(1, min(len(clean_sections), 20))
        return json.dumps(
            {
                "title": str(data.get("title", topic))[:200],
                "subtitle": str(data.get("subtitle", ""))[:200],
                "sections": clean_sections,
                "key_takeaway": str(data.get("key_takeaway", topic))[:300],
                "estimated_pages": int(data.get("estimated_pages", est)),
            }
        )

    # Fallback: parse markdown headings
    lines = text.splitlines()
    title = lines[0].lstrip("#").strip() if lines else topic
    fallback_sections: list[dict[str, Any]] = []
    current_heading = ""
    current_body: list[str] = []

    for line in lines[1:]:
        if line.startswith("#"):
            if current_heading:
                fallback_sections.append(
                    {
                        "heading": current_heading,
                        "body_markdown": "\n".join(current_body).strip(),
                        "callout": None,
                    }
                )
            current_heading = line.lstrip("#").strip()
            current_body = []
        else:
            current_body.append(line)

    if current_heading:
        fallback_sections.append(
            {
                "heading": current_heading,
                "body_markdown": "\n".join(current_body).strip(),
                "callout": None,
            }
        )

    while len(fallback_sections) < _MIN_SECTIONS:
        fallback_sections.append(
            {
                "heading": f"Section {len(fallback_sections) + 1}",
                "body_markdown": "",
                "callout": None,
            }
        )

    return json.dumps(
        {
            "title": title[:200],
            "subtitle": "",
            "sections": fallback_sections[:_MAX_SECTIONS],
            "key_takeaway": text[:200].replace("\n", " "),
            "estimated_pages": max(1, min(len(fallback_sections), 20)),
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
