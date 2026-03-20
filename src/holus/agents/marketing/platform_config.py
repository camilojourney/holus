"""Platform-specific configuration for isolated learning.

Each platform has its own:
- Judge rubric (what makes "good" content)
- Reward weights (which engagement metric matters most)
- Content constraints (character limits, format rules)
- Performance patterns (learned independently)

This is the implementation of the platform isolation design decision:
one codebase, per-platform segmented learning.

Usage::

    config = get_platform_config("linkedin")
    config.judge_rubric  # Platform-specific evaluation criteria
    config.reward_weights  # {"comments": 0.4, "shares": 0.3, ...}
    config.char_limit  # 3000
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformConfig:
    """Configuration for a single platform."""

    platform_id: str
    display_name: str
    char_limit: int
    supported_formats: list[str]
    reward_weights: dict[str, float]
    judge_rubric: str
    posting_rules: list[str] = field(default_factory=list)
    optimal_posting_times: list[str] = field(default_factory=list)
    hashtag_limit: int = 0
    emoji_policy: str = "minimal"
    # Risk routing (SPEC-016)
    risk_tier: str = "low"  # low = auto-queue, high = require approval


# Platform registry — each platform's configuration
PLATFORMS: dict[str, PlatformConfig] = {
    "linkedin": PlatformConfig(
        platform_id="linkedin",
        display_name="LinkedIn",
        char_limit=3000,
        supported_formats=["text_post", "carousel_outline", "video_script"],
        reward_weights={"comments": 0.4, "shares": 0.3, "likes": 0.2, "saves": 0.1},
        judge_rubric=(
            "LinkedIn content evaluation:\n"
            "- hook_strength: Does it stop the scroll in a professional feed? (0-1)\n"
            "- authority_signal: Does it position the author as an expert builder? (0-1)\n"
            "- narrative_arc: Is there a clear setup → insight → takeaway? (0-1)\n"
            "- voice_fidelity: First person, opinionated, no hedging? (0-1)\n"
            "- engagement_potential: Will it spark comments (questions, debate)? (0-1)\n"
        ),
        posting_rules=[
            "No more than 1 post per day",
            "Carousel posts should be 8-10 slides",
            "First line must not start with 'I'",
            "No more than 3 hashtags",
        ],
        optimal_posting_times=["07:00-09:00 ET", "11:30-13:00 ET", "17:00-18:00 ET"],
        hashtag_limit=3,
        risk_tier="low",  # LinkedIn = established, auto-queue

    ),
    "twitter": PlatformConfig(
        platform_id="twitter",
        display_name="Twitter/X",
        char_limit=280,
        supported_formats=["text_post", "thread"],
        reward_weights={"retweets": 0.4, "quotes": 0.3, "replies": 0.2, "likes": 0.1},
        judge_rubric=(
            "Twitter/X content evaluation:\n"
            "- hook_timing: Does the first tweet grab in under 2 seconds? (0-1)\n"
            "- punchiness: Is every word earning its place? (0-1)\n"
            "- ratio_potential: Will it spark debate/disagreement? (0-1)\n"
            "- thread_pacing: Each tweet standalone yet builds? (0-1)\n"
            "- cta_lightness: Organic question, not forced engagement bait? (0-1)\n"
        ),
        posting_rules=[
            "Max 280 chars per tweet",
            "Threads: 5-8 tweets max",
            "No hashtag walls",
        ],
        optimal_posting_times=["08:00-10:00 ET", "12:00-13:00 ET"],
        hashtag_limit=2,
        risk_tier="low",

    ),
    "twitter_x": None,  # type: ignore[dict-item]  # Alias — resolved below
    "instagram": PlatformConfig(
        platform_id="instagram",
        display_name="Instagram",
        char_limit=2200,
        supported_formats=["instagram_caption", "carousel_outline", "video_script"],
        reward_weights={"saves": 0.4, "shares": 0.3, "comments": 0.2, "likes": 0.1},
        judge_rubric=(
            "Instagram content evaluation:\n"
            "- visual_hook: Does the opening line stop the scroll? (for caption-only posts, evaluate hook strength) (0-1)\n"
            "- caption_depth: Is there substance beyond the visual? (0-1)\n"
            "- save_worthiness: Would someone bookmark this for later? (0-1)\n"
            "- authenticity: Does it feel real, not corporate? (0-1)\n"
            "- hashtag_strategy: Relevant, not spammy? (0-1)\n"
        ),
        posting_rules=[
            "Visual-first — image/video required",
            "Captions can be long (2200 chars) but front-load value",
            "5-15 hashtags in a separate block",
        ],
        optimal_posting_times=["11:00-13:00 ET", "19:00-21:00 ET"],
        hashtag_limit=15,
        emoji_policy="moderate",
        risk_tier="high",  # Instagram = visual-first, higher brand risk

    ),
    "threads": PlatformConfig(
        platform_id="threads",
        display_name="Threads",
        char_limit=500,
        supported_formats=["text_post", "instagram_caption"],
        reward_weights={"reposts": 0.3, "quotes": 0.3, "likes": 0.2, "shares": 0.2},
        judge_rubric=(
            "Threads content evaluation:\n"
            "- conversational_tone: Does it feel like talking to a friend? (0-1)\n"
            "- brevity: Is it tight and punchy? (0-1)\n"
            "- native_feel: Does it fit the Threads vibe (not a LinkedIn repost)? (0-1)\n"
            "- discussion_starter: Will people reply? (0-1)\n"
            "- personality: Does the author's personality come through? (0-1)\n"
        ),
        posting_rules=[
            "Max 500 chars",
            "Casual, conversational tone",
            "No hashtags (Threads culture)",
        ],
        optimal_posting_times=["08:00-10:00 ET", "20:00-22:00 ET"],
        hashtag_limit=0,
        risk_tier="low",

    ),
    "tiktok": PlatformConfig(
        platform_id="tiktok",
        display_name="TikTok",
        char_limit=4000,
        supported_formats=["video_script"],
        reward_weights={"watch_time": 0.5, "shares": 0.3, "comments": 0.2},
        judge_rubric=(
            "TikTok content evaluation:\n"
            "- hook_timing: Does it grab in the first 0.5 seconds? (0-1)\n"
            "- retention_prediction: Will viewers watch to the end? (0-1)\n"
            "- trend_relevance: Does it tap into current trends/sounds? (0-1)\n"
            "- educational_value: Does the viewer learn something? (0-1)\n"
            "- replay_value: Would someone watch it twice? (0-1)\n"
        ),
        posting_rules=[
            "Video only — no text posts",
            "60-90 seconds optimal",
            "Hook in first 0.5 seconds",
        ],
        optimal_posting_times=["19:00-22:00 ET"],
        hashtag_limit=5,
        emoji_policy="liberal",
        risk_tier="high",  # TikTok = video-only, high production risk

    ),
    "facebook": PlatformConfig(
        platform_id="facebook",
        display_name="Facebook",
        char_limit=63206,
        supported_formats=["text_post", "video_script"],
        reward_weights={"shares": 0.4, "comments": 0.3, "likes": 0.2, "clicks": 0.1},
        judge_rubric=(
            "Facebook content evaluation:\n"
            "- shareability: Would someone share this with their network? (0-1)\n"
            "- comment_trigger: Does it ask a question or invite discussion? (0-1)\n"
            "- visual_appeal: Is the preview image/thumbnail compelling? (0-1)\n"
            "- value_clarity: Is the benefit clear in the first 2 lines? (0-1)\n"
            "- link_relevance: If a link is included, is it genuinely useful? (0-1)\n"
        ),
        posting_rules=[
            "Front-load value in first 2 lines (before 'See more')",
            "Native video outperforms links",
        ],
        optimal_posting_times=["09:00-11:00 ET", "13:00-15:00 ET"],
        hashtag_limit=3,
        risk_tier="low",

    ),
}

# Resolve alias
PLATFORMS["twitter_x"] = PLATFORMS["twitter"]


def get_platform_config(platform: str) -> PlatformConfig:
    """Get configuration for a platform. Falls back to LinkedIn defaults."""
    config = PLATFORMS.get(platform.lower())
    if config is None:
        config = PLATFORMS["linkedin"]
    return config


def list_platforms() -> list[str]:
    """List all configured platform IDs."""
    return [k for k in PLATFORMS if PLATFORMS[k] is not None and k != "twitter_x"]


def get_judge_rubric(platform: str) -> str:
    """Get the platform-specific judge rubric."""
    return get_platform_config(platform).judge_rubric


def get_reward_weights(platform: str) -> dict[str, float]:
    """Get the platform-specific reward weights."""
    return get_platform_config(platform).reward_weights


# ---------------------------------------------------------------------------
# Content config (externalized in config/content.yaml)
# ---------------------------------------------------------------------------

def load_content_config() -> dict[str, Any]:
    """Load content configuration from config/content.yaml.

    Returns the full config dict. Keys:
      languages.primary, languages.additional,
      platform_risk_overrides, approval, translation.
    """
    from pathlib import Path

    import yaml

    config_path = Path("config/content.yaml")
    if not config_path.exists():
        return {
            "languages": {"primary": "en", "additional": []},
            "platform_risk_overrides": {},
            "approval": {"require_all": True, "auto_approve_after": 0},
            "translation": {"provider": "none", "quality_check": False},
        }
    result: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
    return result


def get_languages() -> dict[str, Any]:
    """Get language configuration: primary + additional languages."""
    cfg = load_content_config()
    result: dict[str, Any] = cfg.get("languages", {"primary": "en", "additional": []})
    return result


def get_effective_risk_tier(platform: str) -> str:
    """Get risk tier for a platform, with config overrides applied."""
    cfg = load_content_config()
    overrides = cfg.get("platform_risk_overrides", {})
    if platform.lower() in overrides:
        result: str = overrides[platform.lower()]
        return result
    return get_platform_config(platform).risk_tier


def requires_approval(platform: str) -> bool:
    """Check if a platform requires explicit approval before queuing."""
    cfg = load_content_config()
    approval = cfg.get("approval", {})
    if approval.get("require_all", True):
        return True
    return get_effective_risk_tier(platform) == "high"
