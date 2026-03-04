"""Content generation: text creation, fallbacks, and platform limit enforcement.

Extracted from agent.py to reduce module size and improve testability.
"""

from __future__ import annotations

import logging
from typing import Any

from holus.agents.marketing.models import ContentDecision, Platform
from holus.agents.marketing.prompts import (
    SONNET_CONTENT_PROMPT,
    format_anti_patterns,
    format_positioning,
    format_product_info,
    format_voice,
)
from holus.integrations.claude_api.client import CachedPrompt, HolusClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLATFORM_CHAR_LIMITS: dict[Platform, int] = {
    Platform.TWITTER: 280,
    Platform.LINKEDIN: 3000,
    Platform.INSTAGRAM: 2200,
    Platform.THREADS: 500,
    Platform.FACEBOOK: 63206,
}

# ---------------------------------------------------------------------------
# Pure functions (no external dependencies)
# ---------------------------------------------------------------------------


def fallback_content_text(decision: ContentDecision) -> str:
    """Generate fallback content with authority-building voice."""
    hook = decision.hook or decision.topic

    if decision.platform is Platform.TWITTER:
        return (
            f"{hook}\n\n"
            f"I learned this building {decision.product}. "
            "One pattern that transfers to any AI team."
        )

    if decision.platform is Platform.LINKEDIN:
        return (
            f"{hook}\n\n"
            f"I built {decision.product} from scratch. "
            "Here's the framework that actually worked:\n\n"
            "1) Start with the smallest testable workflow\n"
            "2) Measure the baseline before optimizing\n"
            "3) Change one variable per iteration\n\n"
            "Most teams skip step 2. That's where the expensive mistakes happen.\n\n"
            "What's the biggest bottleneck in your AI implementation?"
        )

    return (
        f"{hook}\n\n"
        f"Building {decision.product} taught me this: focus on one repeatable pattern "
        "and get it right before scaling.\n\n"
        "What are you building?"
    )


def enforce_platform_limit(text: str, platform: Platform) -> str:
    """Truncate text to platform character limits with ellipsis."""
    limit = PLATFORM_CHAR_LIMITS.get(platform)
    if limit is None or len(text) <= limit:
        return text

    trimmed = text[: max(limit - 3, 0)].rstrip()
    return f"{trimmed}..."


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
# Generation (requires Claude client)
# ---------------------------------------------------------------------------


def generate_text_for_decision(
    *,
    decision: ContentDecision,
    knowledge: dict[str, str],
    products: dict[str, Any],
    brand: dict[str, Any] | None = None,
    claude: HolusClaudeClient,
    anthropic_api_key: str | None,
    sonnet_model: str,
    agent_id: str,
) -> tuple[str, str]:
    """Generate content text for a decision using authority-building prompts.

    Uses Camilo's voice, brand positioning, and anti-patterns from brand.yaml.
    Falls back to template text when API key is unavailable.
    """
    brand = brand or {}
    products_dict = products.get("products", {})
    product_info = format_product_info(decision.product, products_dict)

    if not anthropic_api_key:
        text = fallback_content_text(decision)
        return enforce_platform_limit(text, decision.platform), "template-fallback"

    system_prompt = SONNET_CONTENT_PROMPT.format(
        topic=decision.topic,
        content_pillar=decision.content_pillar,
        hook=decision.hook or "(generate an engaging hook)",
        framework=decision.framework,
        reasoning=decision.reasoning,
        voice=format_voice(brand),
        positioning=format_positioning(brand),
        product_info=product_info,
        anti_patterns=format_anti_patterns(brand),
    )

    response = claude.call(
        cached_prompt=CachedPrompt(system_prompt=system_prompt),
        messages=[{"role": "user", "content": "Generate the final content now."}],
        tier="operational",
        max_tokens=1536,
        temperature=0.4,
        agent_id=agent_id,
    )

    text = extract_response_text(response).strip()
    if not text:
        text = fallback_content_text(decision)

    return enforce_platform_limit(text, decision.platform), sonnet_model
