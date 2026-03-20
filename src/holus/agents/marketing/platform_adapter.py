"""Platform adapter — repurpose content across platforms.

Takes content generated for one platform and adapts it for others.
Each platform has different norms (length, tone, format, hashtags).

Usage::

    adapter = PlatformAdapter()
    adapted = await adapter.repurpose(
        text="Long LinkedIn post...",
        source_platform="linkedin",
        target_platform="twitter",
    )
    # Returns shortened, punchier version for Twitter
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from holus.agents.marketing.platform_config import get_platform_config
from holus.core.llm_proxy import get_proxy_headers, get_proxy_url

logger = logging.getLogger(__name__)

PROXY_URL = get_proxy_url()
PROXY_HEADERS = get_proxy_headers()


REPURPOSE_SYSTEM = """You are a content adapter. You take content written for one platform
and adapt it for another while preserving the core message.

Rules:
- Preserve the thesis (ONE main idea)
- Adapt tone to the target platform's culture
- Respect character limits
- Adjust formatting (hashtags, emojis, structure)
- Do NOT add new claims — only reformat what exists
- Return the adapted text only, no commentary"""


class PlatformAdapter:
    """Adapt content from one platform to another."""

    async def repurpose(
        self,
        text: str,
        source_platform: str,
        target_platform: str,
        *,
        content_type: str = "text_post",
    ) -> dict[str, Any]:
        """Repurpose content for a different platform.

        Returns: {text, platform, char_count, within_limit, format}
        """
        source_config = get_platform_config(source_platform)
        target_config = get_platform_config(target_platform)

        prompt = f"""
<source_platform>{source_config.display_name}</source_platform>
<target_platform>{target_config.display_name}</target_platform>
<target_char_limit>{target_config.char_limit}</target_char_limit>
<target_hashtag_limit>{target_config.hashtag_limit}</target_hashtag_limit>
<target_emoji_policy>{target_config.emoji_policy}</target_emoji_policy>

<target_rules>
{chr(10).join(f"- {r}" for r in target_config.posting_rules)}
</target_rules>

<original_content>
{text}
</original_content>

Adapt this {source_config.display_name} content for {target_config.display_name}.
Return ONLY the adapted text.
"""
        adapted_text = self._call(prompt)

        if not adapted_text:
            # Fallback: truncate to char limit
            adapted_text = text[:target_config.char_limit]

        return {
            "text": adapted_text,
            "platform": target_platform,
            "char_count": len(adapted_text),
            "within_limit": len(adapted_text) <= target_config.char_limit,
            "source_platform": source_platform,
            "format": content_type,
        }

    async def repurpose_to_all(
        self,
        text: str,
        source_platform: str,
        *,
        target_platforms: list[str] | None = None,
        content_type: str = "text_post",
    ) -> list[dict[str, Any]]:
        """Repurpose content to all compatible target platforms.

        Skips the source platform and platforms that don't support the format.
        """
        from holus.agents.marketing.platform_config import list_platforms

        targets = target_platforms or list_platforms()
        results = []

        for target in targets:
            if target == source_platform:
                continue

            target_config = get_platform_config(target)
            if content_type not in target_config.supported_formats:
                continue

            result = await self.repurpose(
                text=text,
                source_platform=source_platform,
                target_platform=target,
                content_type=content_type,
            )
            results.append(result)

        return results

    def _call(self, user_msg: str) -> str:
        """Call LLM via proxy."""
        try:
            payload = {
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [
                    {"role": "system", "content": REPURPOSE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 2048,
                "temperature": 0.3,
            }
            resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Platform adaptation failed: %s", exc)
            return ""


def normalize_engagement(
    analytics: dict[str, Any],
    platform: str,
    *,
    baseline_stats: dict[str, dict[str, float]] | None = None,
) -> float:
    """Normalize engagement metrics across platforms using z-scores.

    Different platforms have different scales:
    - LinkedIn impressions: 100-10,000
    - Instagram reach: 50-5,000
    - Twitter views: 200-50,000

    Without normalization, Twitter views dominate. Z-score normalization
    makes cross-platform comparison meaningful.

    baseline_stats: {platform: {mean: X, std: Y}} — from historical data.
    If not provided, uses raw engagement_rate.
    """
    engagement_rate = analytics.get("engagement_rate", 0.0) or 0.0

    if baseline_stats and platform in baseline_stats:
        stats = baseline_stats[platform]
        mean = stats.get("mean", 0.0)
        std = stats.get("std", 1.0)
        if std > 0:
            z_score = (engagement_rate - mean) / std
            # Convert z-score to 0-1 range using sigmoid
            import math
            return 1 / (1 + math.exp(-z_score))

    # Fallback: cap at 1.0
    return min(engagement_rate / 10, 1.0)
