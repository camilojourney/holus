"""Content repurposing — adapt LinkedIn posts for secondary platforms.

Takes a LinkedIn post (the primary content) and adapts it for Twitter,
Instagram, Threads, and Facebook using Claude Sonnet.  Falls back to
mechanical adaptation when the API is unavailable.

Spec reference: specs/017-authority-engine-agent-update.md (SPEC-004).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from holus.agents.marketing.models import (
    ContentDecision,
    GeneratedPiece,
    Platform,
)
from holus.agents.marketing.prompts import REPURPOSE_PROMPT, format_voice
from holus.integrations.claude_api.client import CachedPrompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform-specific adaptation rules (fed into REPURPOSE_PROMPT)
# ---------------------------------------------------------------------------

PLATFORM_RULES: dict[Platform, dict[str, str]] = {
    Platform.TWITTER: {
        "max_chars": "280 per tweet",
        "style": "Condensed, punchy. One key insight per tweet. No hashtags unless viral.",
        "format": "ALWAYS format as a numbered thread: 1/, 2/, 3/... Each tweet MUST be under 280 chars. Separate tweets with blank lines.",
        "thread_format": "ALWAYS format as a numbered thread (1/, 2/, 3/...). Each tweet MUST be under 280 chars. Split at natural thought boundaries. First tweet is the hook.",
        "adapt": "Extract the core insight. Lead with the hook in tweet 1/. Expand the argument across 3-5 tweets. Cut all filler. Keep Camilo's voice — first person, contractions, builder mindset.",
        "cta": "'Reply' or 'RT if you agree' (not DM). Put CTA in last tweet.",
        "links": "OK in tweets (no penalty like LinkedIn).",
    },
    Platform.INSTAGRAM: {
        "max_chars": "2200",
        "style": "Visual-friendly caption. Hook in first line (shows in feed preview). 50-120 words — much shorter than LinkedIn.",
        "format": "Shorter paragraphs. Strategic line breaks. 10-15 relevant hashtags at the very end.",
        "adapt": "Condense the LinkedIn post significantly. Keep the hook and core insight, cut the supporting evidence. Add a clear CTA. Use emojis sparingly (1-2 max). Keep first person voice.",
        "cta": "'Save this' or 'Link in bio'.",
    },
    Platform.THREADS: {
        "max_chars": "500",
        "style": "Conversational, informal. Like texting a tech friend. 30-80 words max.",
        "format": "Short post. No hashtags. One core insight only — strip all setup and context.",
        "adapt": "Extract the single most interesting claim or insight from the LinkedIn post. Direct, casual tone. Ask a question to invite replies. First person. Under 500 chars. NEVER use 'here\\'s the thing', 'honestly', 'let\\'s dive in', or other filler openers.",
        "cta": "'What do you think?' (community-oriented).",
    },
    Platform.FACEBOOK: {
        "max_chars": "5000",
        "style": "Similar to LinkedIn but slightly warmer and more personal.",
        "format": "Can be longer. Include context for a broader audience.",
        "adapt": "Keep full content. Slightly warmer tone. OK to add brief personal context. Soft CTA.",
        "cta": "'Comment if this resonates'.",
        "bilingual_note": "Phase 2: auto-translate to Spanish via DeepL.",
    },
}

# Character limits used for enforcement (mirrors agent._PLATFORM_CHAR_LIMITS)
CHAR_LIMITS: dict[Platform, int] = {
    Platform.TWITTER: 280,
    Platform.INSTAGRAM: 2200,
    Platform.THREADS: 500,
    Platform.FACEBOOK: 63206,
}

# Default secondary platforms to repurpose to (LinkedIn is the primary)
REPURPOSE_TARGETS: list[Platform] = [
    Platform.TWITTER,
    Platform.INSTAGRAM,
    Platform.THREADS,
    Platform.FACEBOOK,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def repurpose_content(
    *,
    original_text: str,
    decision: ContentDecision,
    claude_client: Any,
    brand: dict[str, Any],
    cycle_id: str,
    piece_index: int,
    agent_id: str = "marketing-agent",
    targets: list[Platform] | None = None,
) -> list[GeneratedPiece]:
    """Adapt a LinkedIn post for secondary platforms.

    Parameters
    ----------
    original_text:
        The full LinkedIn post text to repurpose.
    decision:
        The ContentDecision that produced the LinkedIn post.
    claude_client:
        HolusClaudeClient instance (or mock) with a `.call()` method.
    brand:
        Brand identity dict (from config/brand.yaml).
    cycle_id:
        Current marketing cycle identifier.
    piece_index:
        Index of the content decision within this cycle (for piece_id).
    agent_id:
        Agent identifier for Claude API cost tracking.
    targets:
        Override default REPURPOSE_TARGETS if needed.

    Returns
    -------
    list[GeneratedPiece]
        One GeneratedPiece per secondary platform, ready for queue.
    """
    targets = targets or REPURPOSE_TARGETS
    voice = format_voice(brand)
    pieces: list[GeneratedPiece] = []

    for target in targets:
        rules = PLATFORM_RULES.get(target)
        if rules is None:
            logger.warning("No repurpose rules for platform %s, skipping", target)
            continue

        adapted_text = _adapt_for_platform(
            original_text=original_text,
            target=target,
            rules=rules,
            voice=voice,
            claude_client=claude_client,
            agent_id=agent_id,
        )

        piece = GeneratedPiece(
            piece_id=f"{cycle_id}-{piece_index}-{target.value}-{uuid4().hex[:8]}",
            decision=decision,
            text=adapted_text,
            platform=target,
            model_used=getattr(claude_client, "sonnet_model", "claude-sonnet-4-6"),
        )
        pieces.append(piece)

    logger.info("Repurposed LinkedIn post to %d secondary platforms", len(pieces))
    return pieces


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _adapt_for_platform(
    *,
    original_text: str,
    target: Platform,
    rules: dict[str, str],
    voice: str,
    claude_client: Any,
    agent_id: str,
) -> str:
    """Call Claude Sonnet to adapt the text, falling back to mechanical adaptation."""
    try:
        adapted = _claude_adapt(
            original_text=original_text,
            target=target,
            rules=rules,
            voice=voice,
            claude_client=claude_client,
            agent_id=agent_id,
        )
        if adapted:
            return _enforce_limit(adapted, target)
    except Exception:
        logger.exception("Claude adaptation failed for %s, using fallback", target.value)

    return _enforce_limit(_fallback_adapt(original_text, target), target)


def _claude_adapt(
    *,
    original_text: str,
    target: Platform,
    rules: dict[str, str],
    voice: str,
    claude_client: Any,
    agent_id: str,
) -> str:
    """Use Claude Sonnet to intelligently adapt content."""
    system_prompt = REPURPOSE_PROMPT.format(
        target_platform=target.value.capitalize(),
        original_text=original_text,
        platform_rules=_format_rules(rules),
        voice=voice,
    )

    response = claude_client.call(
        cached_prompt=CachedPrompt(system_prompt=system_prompt),
        messages=[{"role": "user", "content": "Adapt this content now."}],
        tier="operational",
        max_tokens=512,
        temperature=0.3,
        agent_id=agent_id,
    )

    # Extract text from response (same pattern as agent._extract_response_text)
    blocks = getattr(response, "content", [])
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts).strip()


def _format_rules(rules: dict[str, str]) -> str:
    """Format platform rules dict into readable prompt text."""
    lines: list[str] = []
    for key, value in rules.items():
        label = key.replace("_", " ").capitalize()
        lines.append(f"- **{label}:** {value}")
    return "\n".join(lines)


def _enforce_limit(text: str, platform: Platform) -> str:
    """Enforce platform character limit, truncating at last complete sentence.

    For Twitter: if the text exceeds 280 chars and is not already formatted
    as a numbered thread, split into a numbered thread instead of truncating.
    """
    limit = CHAR_LIMITS.get(platform)
    if limit is None or len(text) <= limit:
        return text

    # Twitter special case: split into thread instead of truncating
    if platform == Platform.TWITTER and not _is_thread(text):
        return _split_into_thread(text)

    # Generic truncation for other platforms
    budget = max(limit - 3, 0)
    candidate = text[:budget]
    # Find last sentence-ending punctuation
    for sep in ("\n\n", ".\n", ". ", ".\u200b"):
        pos = candidate.rfind(sep)
        if pos > budget // 2:  # don't cut too early
            return candidate[: pos + len(sep)].rstrip() + "..."
    # Fallback: cut at last space to avoid mid-word truncation
    last_space = candidate.rfind(" ")
    if last_space > budget // 2:
        return candidate[:last_space].rstrip() + "..."
    return candidate.rstrip() + "..."


def _is_thread(text: str) -> bool:
    """Check if text is already formatted as a numbered thread."""
    return "1/" in text and "2/" in text


def _split_into_thread(text: str, max_tweet_chars: int = 260) -> str:
    """Split text into a numbered Twitter thread at sentence boundaries.

    Each tweet is prefixed with ``N/`` and kept under *max_tweet_chars*
    (default 260 to leave room for the number prefix and whitespace).
    Tweets are separated by blank lines.
    """
    import re

    # Split into sentences (keep the delimiter attached)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    tweets: list[str] = []
    current = ""

    for sentence in sentences:
        # Check if adding this sentence would exceed the limit
        # Account for the thread prefix like "1/ " (up to "99/ " = 4 chars)
        prefix_len = len(f"{len(tweets) + 1}/ ")
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) + prefix_len <= max_tweet_chars:
            current = candidate
        else:
            # Save the current tweet if it has content
            if current:
                tweets.append(current)
            # Start a new tweet with this sentence
            # If the sentence itself is too long, truncate it
            new_prefix_len = len(f"{len(tweets) + 1}/ ")
            if len(sentence) + new_prefix_len > max_tweet_chars:
                current = sentence[: max_tweet_chars - new_prefix_len - 3] + "..."
            else:
                current = sentence

    # Don't forget the last chunk
    if current:
        tweets.append(current)

    # Format as numbered thread
    numbered = [f"{i + 1}/ {tweet}" for i, tweet in enumerate(tweets)]
    return "\n\n".join(numbered)


def _fallback_adapt(original_text: str, target: Platform) -> str:
    """Mechanical fallback when Claude is unavailable.

    Each platform gets a reasonable adaptation without AI:
    - Twitter: first sentence or truncated to 280
    - Instagram: shortened version with hashtag placeholder
    - Threads: first paragraph, conversational
    - Facebook: full text (effectively unlimited)
    """
    if target == Platform.TWITTER:
        # Split into a numbered thread at sentence boundaries
        if len(original_text) <= 280:
            return f"1/ {original_text}"
        return _split_into_thread(original_text)

    if target == Platform.INSTAGRAM:
        # Use LinkedIn text, trimmed to limit
        text = original_text[:2100] if len(original_text) > 2100 else original_text
        return text + "\n\n#AI #Builder #Tech"

    if target == Platform.THREADS:
        # First paragraph, keep it short
        paragraphs = [p.strip() for p in original_text.split("\n\n") if p.strip()]
        if paragraphs:
            first = paragraphs[0]
            if len(first) <= 500:
                return first
            return first[:497] + "..."
        return original_text[:497] + "..." if len(original_text) > 500 else original_text

    if target == Platform.FACEBOOK:
        # Full text as-is (Facebook has no practical limit for this use case)
        return original_text

    return original_text
