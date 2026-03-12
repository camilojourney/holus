"""Diagram specialist creator.

Produces Mermaid diagram definitions for architecture explanations, workflows,
and comparisons. The diagram renders to a PNG image before posting.

Best for:
- System architecture explanations
- Process flows / decision trees
- Before/after comparisons (using flowchart)
- Timeline or sequence diagrams

The raw_content JSON schema::

    {
        "diagram_type": "flowchart | sequence | architecture | comparison | timeline",
        "mermaid_code": "graph TD\n    A[Start] --> B[End]",
        "explanation": "Text explaining the diagram",
        "title": "Diagram title"
    }
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..models import ContentIdea, ContentPiece, FormatType
from .base import BaseSpecialist

logger = logging.getLogger(__name__)

_VALID_DIAGRAM_TYPES = frozenset(
    {"flowchart", "sequence", "architecture", "comparison", "timeline"}
)
_FALLBACK_MERMAID = "graph TD\n    A[Start] --> B[Process] --> C[End]"


class DiagramCreator(BaseSpecialist):
    """Creates Mermaid diagram definitions for visual architecture and flow content.

    Does NOT render the diagram — rendering to PNG is downstream (Pilaster or
    an external Mermaid CLI). Holus produces the definition; the silo renders it.
    """

    format_type = FormatType.DIAGRAM

    async def create(self, idea: ContentIdea, context: dict[str, Any]) -> ContentPiece:
        """Create a diagram content piece.

        Args:
            idea: The content idea to create a diagram for.
            context: May contain:
                - ``claude_client``: Claude API client.
                - ``brand``: Brand identity dict.
                - ``products``: Products dict.

        Returns:
            A :class:`ContentPiece` with diagram JSON in ``raw_content``.
        """
        topic = idea.topic
        product = idea.product
        pillar = idea.content_pillar
        notes = idea.notes

        claude_client = context.get("claude_client")
        products = context.get("products", {})

        if claude_client is not None:
            raw = await self._call_claude(claude_client, topic, product, pillar, notes, products)
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
        products: dict[str, Any],
    ) -> str:
        """Call Claude to generate a Mermaid diagram; return JSON string."""
        product_ctx = _extract_product(products, product)

        system_prompt = (
            "You are a diagram content specialist. Create a clear Mermaid diagram "
            "for the given topic. Respond with ONLY a valid JSON object in this format:\n"
            '{"diagram_type": "flowchart", "mermaid_code": "graph TD\\n    ...", '
            '"explanation": "...", "title": "..."}\n\n'
            "diagram_type must be one of: flowchart, sequence, architecture, comparison, timeline\n"
            "mermaid_code must be valid Mermaid syntax.\n"
            f"Product context: {product_ctx}"
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
                agent_id="diagram-specialist",
            )
            text = response if isinstance(response, str) else str(response)
            return _parse_diagram_response(text, topic)
        except Exception:
            logger.exception("Claude call failed in DiagramCreator; using fallback")
            return self._build_fallback(topic)

    def _build_fallback(self, topic: str) -> str:
        """Construct a minimal diagram skeleton."""
        mermaid = (
            f"graph TD\n"
            f"    A[Start: {topic[:30]}] --> B[Step 1]\n"
            f"    B --> C[Step 2]\n"
            f"    C --> D[Result]\n"
        )
        return json.dumps(
            {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid,
                "explanation": f"A high-level overview of {topic}.",
                "title": topic[:100],
            }
        )


def _parse_diagram_response(text: str, topic: str) -> str:
    """Parse Claude's JSON output into a canonical diagram JSON string."""
    for raw in (text, _extract_json_block(text)):
        if not raw:
            continue
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue

        mermaid_code = str(data.get("mermaid_code", "")).strip()
        if not mermaid_code:
            break

        diagram_type = str(data.get("diagram_type", "flowchart")).lower()
        if diagram_type not in _VALID_DIAGRAM_TYPES:
            diagram_type = "flowchart"

        return json.dumps(
            {
                "diagram_type": diagram_type,
                "mermaid_code": mermaid_code,
                "explanation": str(data.get("explanation", ""))[:1000],
                "title": str(data.get("title", topic))[:200],
            }
        )

    # Try extracting a raw mermaid code block
    mermaid_match = re.search(
        r"```(?:mermaid)?\s*(graph|flowchart|sequenceDiagram|classDiagram|gantt|timeline)(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    mermaid_code = _FALLBACK_MERMAID
    if mermaid_match:
        mermaid_code = (mermaid_match.group(1) + mermaid_match.group(2)).strip()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:200] if lines else topic
    explanation = " ".join(lines[1:3])[:500] if len(lines) > 1 else text[:200]

    return json.dumps(
        {
            "diagram_type": "flowchart",
            "mermaid_code": mermaid_code,
            "explanation": explanation,
            "title": title,
        }
    )


def _extract_json_block(text: str) -> str | None:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else None


def _extract_product(products: dict[str, Any], product_key: str) -> str:
    try:
        plist = products.get("products", products)
        info = plist.get(product_key, {})
        name = info.get("name", product_key)
        tagline = info.get("tagline", "")
        return f"{name}: {tagline}" if tagline else name
    except Exception:
        return ""
