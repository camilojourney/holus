"""Content Router — maps a ContentIdea to the list of FormatTypes to produce.

The router is the first step in the Content Factory pipeline. It reads analytics
context and the idea's format_hint (if any) to decide which specialist formats
should be produced for this idea.

Routing rules (in priority order):
1. Explicit ``format_hint`` on the ContentIdea → use it directly.
2. Keyword analysis of ``idea.topic`` → match against known format signals.
3. Analytics context hints (e.g., "carousel" was top format this week).
4. Fallback to TEXT for all platforms that accept text-only content.

Instagram is excluded from text-only routing because it requires media.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import (
    MEDIA_REQUIRED_PLATFORMS,
    ContentIdea,
    FormatType,
    PlatformType,
)

logger = logging.getLogger(__name__)

# Keyword signals that indicate a specific format.
# Keys must match FormatType values. Order matters — checked top-down.
_FORMAT_KEYWORDS: dict[FormatType, list[str]] = {
    FormatType.DIAGRAM: [
        "diagram",
        "flowchart",
        "architecture",
        "system design",
        "framework",
        "workflow",
        "chart",
        "comparison chart",
    ],
    FormatType.CAROUSEL: [
        "carousel",
        "slide",
        "swipe",
        "step by step",
        "step-by-step",
        "how to",
        "tips",
        "list of",
        "top 5",
        "top 10",
        "checklist",
    ],
    FormatType.PDF: [
        "pdf",
        "guide",
        "whitepaper",
        "ebook",
        "playbook",
        "report",
        "template",
        "case study",
        "deep dive",
    ],
    FormatType.VIDEO_BRIEF: [
        "video",
        "reel",
        "short",
        "clip",
        "watch",
        "demo",
        "walkthrough",
        "screencast",
        "tutorial video",
    ],
    # TEXT is the fallback — no keywords needed
}

# Platforms that work with text-only content (no media needed).
_TEXT_SAFE_PLATFORMS: list[PlatformType] = [
    p for p in PlatformType if p not in MEDIA_REQUIRED_PLATFORMS
]

# Which platforms are targeted by default for each format.
_FORMAT_DEFAULT_PLATFORMS: dict[FormatType, list[PlatformType]] = {
    FormatType.CAROUSEL: [
        PlatformType.LINKEDIN,
        PlatformType.INSTAGRAM,
        PlatformType.FACEBOOK,
    ],
    FormatType.PDF: [
        PlatformType.LINKEDIN,
        PlatformType.FACEBOOK,
    ],
    FormatType.DIAGRAM: [
        PlatformType.LINKEDIN,
        PlatformType.TWITTER,
        PlatformType.THREADS,
        PlatformType.FACEBOOK,
    ],
    FormatType.VIDEO_BRIEF: [
        PlatformType.INSTAGRAM,
        PlatformType.TWITTER,
        PlatformType.THREADS,
        PlatformType.FACEBOOK,
        PlatformType.LINKEDIN,
    ],
    FormatType.TEXT: _TEXT_SAFE_PLATFORMS,
}

# Maps format_hint strings (from LLM or user) to FormatType.
_HINT_MAP: dict[str, FormatType] = {
    "carousel": FormatType.CAROUSEL,
    "pdf": FormatType.PDF,
    "diagram": FormatType.DIAGRAM,
    "video_brief": FormatType.VIDEO_BRIEF,
    "video": FormatType.VIDEO_BRIEF,
    "text": FormatType.TEXT,
    "post": FormatType.TEXT,
    "thread": FormatType.TEXT,
    "narrative": FormatType.TEXT,
}


class ContentRouter:
    """Routes a ContentIdea to the list of FormatTypes that should be produced.

    Usage::

        router = ContentRouter()
        formats = await router.route(idea, analytics={"top_format": "carousel"})
        # formats → [FormatType.CAROUSEL]

    The router is intentionally stateless — all routing state comes from the
    inputs (idea + analytics). No LLM call is made; routing is deterministic.
    This keeps the factory fast and auditable.
    """

    async def route(
        self,
        idea: ContentIdea,
        analytics: dict[str, Any],
    ) -> list[FormatType]:
        """Determine which formats to produce for the given idea.

        Args:
            idea: The content idea to route.
            analytics: Analytics context dict. Recognised keys:
                - ``top_format``: Format string that performed best recently
                  (e.g., ``"carousel"``). Used as a soft signal when no
                  format_hint or keyword match is found.

        Returns:
            A non-empty list of :class:`FormatType` values to produce.
            Typically a single format, but may include multiple when the
            idea naturally maps to several (e.g., a tutorial → carousel + text).
        """
        # --- 1. Explicit format_hint on the idea --------------------------------
        if idea.format_hint:
            hint_fmt = _HINT_MAP.get(idea.format_hint.lower().strip())
            if hint_fmt is not None:
                logger.debug("Routing by format_hint '%s' → %s", idea.format_hint, hint_fmt.value)
                return [hint_fmt]
            logger.warning(
                "Unknown format_hint '%s' on idea '%s'; continuing to keyword analysis",
                idea.format_hint,
                idea.topic[:60],
            )

        # --- 2. Keyword analysis of topic ---------------------------------------
        topic_lower = idea.topic.lower()
        for fmt, keywords in _FORMAT_KEYWORDS.items():
            for kw in keywords:
                if kw in topic_lower:
                    logger.debug("Routing by keyword '%s' in topic → %s", kw, fmt.value)
                    return [fmt]

        # --- 3. Analytics context -----------------------------------------------
        top_format_str = analytics.get("top_format", "")
        if top_format_str:
            analytics_fmt = _HINT_MAP.get(top_format_str.lower().strip())
            if analytics_fmt is not None and analytics_fmt != FormatType.TEXT:
                logger.debug(
                    "Routing by analytics top_format '%s' → %s",
                    top_format_str,
                    analytics_fmt.value,
                )
                return [analytics_fmt]

        # --- 4. Fallback to TEXT ------------------------------------------------
        logger.debug("No routing signal found for idea '%s'; defaulting to TEXT", idea.topic[:60])
        return [FormatType.TEXT]

    def target_platforms(self, format_type: FormatType) -> list[PlatformType]:
        """Return the default target platforms for a given format.

        This is a convenience helper for callers that need to know which
        platforms to frame content for after routing.

        Args:
            format_type: The format produced by a specialist.

        Returns:
            List of :class:`PlatformType` values suitable for this format.
        """
        return list(_FORMAT_DEFAULT_PLATFORMS.get(format_type, _TEXT_SAFE_PLATFORMS))
