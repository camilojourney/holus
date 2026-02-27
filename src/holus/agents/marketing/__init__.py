"""Marketing agent — content strategy and creation.

The marketing agent observes analytics, decides what content to create,
generates platform-specific posts, and learns from results.
"""

from __future__ import annotations

__all__ = [
    "OPUS_STRATEGY_PROMPT",
    "SONNET_CONTENT_PROMPT",
    "ContentDecision",
    "ContentType",
    "GeneratedPiece",
    "MarketingAgent",
    "MarketingCycleReport",
    "Platform",
    "format_platform_guidelines",
    "format_product_info",
]

from holus.agents.marketing.agent import MarketingAgent
from holus.agents.marketing.models import (
    ContentDecision,
    ContentType,
    GeneratedPiece,
    MarketingCycleReport,
    Platform,
)
from holus.agents.marketing.prompts import (
    OPUS_STRATEGY_PROMPT,
    SONNET_CONTENT_PROMPT,
    format_platform_guidelines,
    format_product_info,
)
