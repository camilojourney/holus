"""JSON parsing: decode LLM responses, coerce content decisions.

Extracted from agent.py to reduce module size and improve testability.
Also consolidates ``decode_json_payload`` / ``extract_response_text`` that
were duplicated across agent.py, niche_research.py, and content_generation.py.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from holus.agents.marketing.models import (
    ContentDecision,
    ContentType,
    Platform,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alias lookup tables (moved from MarketingAgent class attributes)
# ---------------------------------------------------------------------------

PLATFORM_ALIASES: dict[str, Platform] = {
    "linkedin": Platform.LINKEDIN,
    "twitter": Platform.TWITTER,
    "x": Platform.TWITTER,
    "tiktok": Platform.TIKTOK,
    "instagram": Platform.INSTAGRAM,
    "facebook": Platform.FACEBOOK,
    "threads": Platform.THREADS,
    "youtube": Platform.YOUTUBE,
    "youtube_shorts": Platform.YOUTUBE,
    "yt_shorts": Platform.YOUTUBE,
}

CONTENT_TYPE_ALIASES: dict[str, ContentType] = {
    "tutorial": ContentType.TUTORIAL,
    "demo": ContentType.DEMO,
    "tips": ContentType.TIPS,
    "thread": ContentType.THREAD,
    "case_study": ContentType.CASE_STUDY,
    "carousel": ContentType.CAROUSEL,
    "video_reel": ContentType.VIDEO_REEL,
    "announcement": ContentType.ANNOUNCEMENT,
    "educational": ContentType.EDUCATIONAL,
    "technical_post": ContentType.EDUCATIONAL,
    "before_after": ContentType.DEMO,
}

# ---------------------------------------------------------------------------
# Pure helpers (no external dependencies)
# ---------------------------------------------------------------------------


def try_json_loads(text: str) -> Any | None:
    """Safely attempt ``json.loads``; return *None* on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def decode_json_payload(text: str) -> Any | None:
    """Extract a JSON object or array from LLM response text.

    Tries in order: direct parse, fenced code blocks, bare ``[...]`` / ``{...}``.
    """
    stripped = text.strip()
    if not stripped:
        return None

    direct = try_json_loads(stripped)
    if direct is not None:
        return direct

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
    for block in fenced_blocks:
        parsed = try_json_loads(block.strip())
        if parsed is not None:
            return parsed

    left = stripped.find("[")
    right = stripped.rfind("]")
    if left != -1 and right != -1 and right > left:
        parsed = try_json_loads(stripped[left : right + 1])
        if parsed is not None:
            return parsed

    left = stripped.find("{")
    right = stripped.rfind("}")
    if left != -1 and right != -1 and right > left:
        parsed = try_json_loads(stripped[left : right + 1])
        if parsed is not None:
            return parsed

    return None


def extract_response_text(response: Any) -> str:
    """Extract text content from a Claude API response."""
    blocks = getattr(response, "content", [])
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Content decision parsing
# ---------------------------------------------------------------------------


def coerce_decision(payload: Any) -> ContentDecision | None:
    """Coerce a raw dict (from LLM JSON) into a validated ``ContentDecision``.

    Returns *None* for invalid payloads instead of raising.
    """
    if not isinstance(payload, dict):
        return None

    platform_raw = str(payload.get("platform", "linkedin")).strip().lower()
    content_type_raw = str(payload.get("content_type", "tutorial")).strip().lower()

    platform = PLATFORM_ALIASES.get(platform_raw, Platform.LINKEDIN)
    content_type = CONTENT_TYPE_ALIASES.get(content_type_raw, ContentType.TUTORIAL)

    priority_value = 1
    try:
        priority_value = int(payload.get("priority", 1) or 1)
    except (TypeError, ValueError):
        priority_value = 1

    estimated_engagement = str(payload.get("estimated_engagement", "medium")).strip()

    try:
        return ContentDecision(
            product=str(payload.get("product", "pilaster")).strip().lower(),
            platform=platform,
            content_type=content_type,
            content_pillar=str(payload.get("content_pillar", "builder_stories")).strip(),
            topic=str(payload.get("topic", "Product tutorial")).strip(),
            hook=str(payload.get("hook", "")).strip(),
            framework=str(payload.get("framework", "original")).strip(),
            reasoning=str(payload.get("reasoning", "Value-first educational content")).strip(),
            priority=priority_value,
            estimated_engagement=estimated_engagement,
            repurpose_notes=str(payload.get("repurpose_notes", "")).strip(),
        )
    except (ValidationError, ValueError, TypeError):
        logger.warning("Skipping invalid content decision: %s", payload)
        return None


def parse_content_decisions(response_text: str) -> list[ContentDecision]:
    """Parse LLM response text into a list of ``ContentDecision`` objects."""
    payload = decode_json_payload(response_text)
    if payload is None:
        return []

    items: list[dict[str, Any]]
    if isinstance(payload, list):
        items = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        items = [payload]
    else:
        return []

    decisions: list[ContentDecision] = []
    for item in items:
        decision = coerce_decision(item)
        if decision is not None:
            decisions.append(decision)
    return decisions
