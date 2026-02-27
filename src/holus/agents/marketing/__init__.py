"""Marketing agent — content strategy and creation.

The marketing agent observes analytics, decides what content to create,
generates platform-specific posts, and learns from results.
"""

from __future__ import annotations

__all__ = [
    "ContentDecision",
    "ContentType",
    "GeneratedPiece",
    "MarketingAgent",
    "MarketingCycleReport",
    "Platform",
]

from holus.agents.marketing.agent import MarketingAgent
from holus.agents.marketing.models import (
    ContentDecision,
    ContentType,
    GeneratedPiece,
    MarketingCycleReport,
    Platform,
)
