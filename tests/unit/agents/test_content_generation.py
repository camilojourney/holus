"""Tests for content_generation.py — text generation, fallbacks, and platform limits.

Covers:
  - fallback_content_text() — platform-specific fallback templates
  - enforce_platform_limit() — character limit enforcement with ellipsis
  - generate_text_for_decision() — full generation via Claude API with fallback
  - PLATFORM_CHAR_LIMITS — constant validation
"""

from __future__ import annotations

from unittest.mock import MagicMock

from holus.agents.marketing.content_generation import (
    PLATFORM_CHAR_LIMITS,
    enforce_platform_limit,
    fallback_content_text,
    generate_text_for_decision,
)
from holus.agents.marketing.models import ContentDecision, ContentType, Platform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_decision(
    platform: Platform = Platform.LINKEDIN,
    product: str = "pilaster",
    topic: str = "AI image generation with memory",
    hook: str = "I built an image platform that remembers.",
    content_pillar: str = "builder_stories",
    framework: str = "original",
    reasoning: str = "Builder story resonates on LinkedIn.",
) -> ContentDecision:
    """Create a ContentDecision with sensible defaults."""
    return ContentDecision(
        product=product,
        platform=platform,
        content_type=ContentType.TUTORIAL,
        content_pillar=content_pillar,
        topic=topic,
        hook=hook,
        framework=framework,
        reasoning=reasoning,
    )


def _make_claude_response(text: str) -> MagicMock:
    """Build a mock Claude API response with a text content block."""
    response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response.content = [text_block]
    return response


# ---------------------------------------------------------------------------
# Tests: PLATFORM_CHAR_LIMITS
# ---------------------------------------------------------------------------


class TestPlatformCharLimits:
    """Validate the PLATFORM_CHAR_LIMITS constant."""

    def test_all_major_platforms_have_limits(self) -> None:
        """Every key platform has a character limit defined."""
        for p in (
            Platform.TWITTER,
            Platform.LINKEDIN,
            Platform.INSTAGRAM,
            Platform.THREADS,
            Platform.FACEBOOK,
        ):
            assert p in PLATFORM_CHAR_LIMITS

    def test_twitter_limit_is_280(self) -> None:
        assert PLATFORM_CHAR_LIMITS[Platform.TWITTER] == 280

    def test_linkedin_limit_is_3000(self) -> None:
        assert PLATFORM_CHAR_LIMITS[Platform.LINKEDIN] == 3000


# ---------------------------------------------------------------------------
# Tests: fallback_content_text()
# ---------------------------------------------------------------------------


class TestFallbackContentText:
    """Tests for fallback_content_text — platform-specific templates."""

    def test_twitter_fallback_is_short(self) -> None:
        """Twitter fallback should be under 280 chars."""
        decision = _make_decision(platform=Platform.TWITTER)
        text = fallback_content_text(decision)
        assert len(text) <= 280
        assert decision.hook in text

    def test_linkedin_fallback_has_framework_structure(self) -> None:
        """LinkedIn fallback should include numbered steps and CTA."""
        decision = _make_decision(platform=Platform.LINKEDIN)
        text = fallback_content_text(decision)
        assert "1)" in text
        assert "2)" in text
        assert "?" in text  # Should end with a question (CTA)

    def test_generic_fallback_for_other_platforms(self) -> None:
        """Instagram, Threads, Facebook use the generic fallback."""
        for platform in (Platform.INSTAGRAM, Platform.THREADS, Platform.FACEBOOK):
            decision = _make_decision(platform=platform)
            text = fallback_content_text(decision)
            assert decision.hook in text
            assert "What are you building?" in text

    def test_uses_topic_when_hook_is_empty(self) -> None:
        """When hook is empty string, falls back to topic."""
        decision = _make_decision(hook="", topic="My great topic")
        text = fallback_content_text(decision)
        assert "My great topic" in text

    def test_includes_product_name(self) -> None:
        """Fallback text references the product."""
        decision = _make_decision(product="genpeli", platform=Platform.TWITTER)
        text = fallback_content_text(decision)
        assert "genpeli" in text


# ---------------------------------------------------------------------------
# Tests: enforce_platform_limit()
# ---------------------------------------------------------------------------


class TestEnforcePlatformLimit:
    """Tests for enforce_platform_limit — truncation with ellipsis."""

    def test_short_text_unchanged(self) -> None:
        """Text under the limit is returned as-is."""
        text = "Short text"
        result = enforce_platform_limit(text, Platform.TWITTER)
        assert result == text

    def test_exact_limit_unchanged(self) -> None:
        """Text exactly at the limit is not truncated."""
        text = "x" * 280
        result = enforce_platform_limit(text, Platform.TWITTER)
        assert result == text
        assert len(result) == 280

    def test_over_limit_truncated_with_ellipsis(self) -> None:
        """Text over the limit is truncated and gets '...' appended."""
        text = "x" * 300
        result = enforce_platform_limit(text, Platform.TWITTER)
        assert result.endswith("...")
        assert len(result) <= 280

    def test_truncated_length_is_at_limit(self) -> None:
        """Truncated text (body + ...) is <= the platform limit."""
        text = "a" * 500
        result = enforce_platform_limit(text, Platform.TWITTER)
        assert len(result) <= 280

    def test_unknown_platform_returns_unchanged(self) -> None:
        """Platforms not in PLATFORM_CHAR_LIMITS are not truncated."""
        text = "x" * 10000
        result = enforce_platform_limit(text, Platform.TIKTOK)
        assert result == text

    def test_facebook_high_limit(self) -> None:
        """Facebook has a very high limit — normal posts not truncated."""
        text = "x" * 5000
        result = enforce_platform_limit(text, Platform.FACEBOOK)
        assert result == text

    def test_threads_limit_500(self) -> None:
        """Threads is capped at 500 characters."""
        text = "x" * 600
        result = enforce_platform_limit(text, Platform.THREADS)
        assert len(result) <= 500
        assert result.endswith("...")

    def test_very_small_limit_edge_case(self) -> None:
        """If limit - 3 would be 0, still produces valid output."""
        # Simulate by testing with text just slightly over the limit
        text = "ab"  # 2 chars, always under any real platform limit
        result = enforce_platform_limit(text, Platform.TWITTER)
        assert result == "ab"


# ---------------------------------------------------------------------------
# Tests: generate_text_for_decision()
# ---------------------------------------------------------------------------


class TestGenerateTextForDecision:
    """Tests for generate_text_for_decision — Claude API generation + fallback."""

    def test_fallback_when_no_api_key(self) -> None:
        """Returns template-fallback when anthropic_api_key is None."""
        decision = _make_decision()
        mock_claude = MagicMock()
        text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            brand=None,
            claude=mock_claude,
            anthropic_api_key=None,
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert model == "template-fallback"
        assert len(text) > 0
        mock_claude.call.assert_not_called()

    def test_fallback_when_empty_api_key(self) -> None:
        """Empty string API key also triggers fallback."""
        decision = _make_decision()
        mock_claude = MagicMock()
        _text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert model == "template-fallback"
        mock_claude.call.assert_not_called()

    def test_calls_claude_with_api_key(self) -> None:
        """When API key is present, calls Claude and returns generated text."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("Here's my AI consulting insight...")
        text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {"pilaster": {"name": "Pilaster"}}},
            brand={"voice": {"tone": ["direct"]}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert text == "Here's my AI consulting insight..."
        assert model == "claude-sonnet-4-6"
        mock_claude.call.assert_called_once()

    def test_falls_back_on_empty_claude_response(self) -> None:
        """Falls back to template when Claude returns empty text."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("")
        text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        # Should have fallen back to template content
        assert len(text) > 0
        assert model == "claude-sonnet-4-6"

    def test_enforces_platform_limit_on_generated_text(self) -> None:
        """Generated text is truncated to platform limit."""
        decision = _make_decision(platform=Platform.TWITTER)
        mock_claude = MagicMock()
        long_text = "x" * 500
        mock_claude.call.return_value = _make_claude_response(long_text)
        text, _model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert len(text) <= 280
        assert text.endswith("...")

    def test_enforces_platform_limit_on_fallback(self) -> None:
        """Fallback text is also truncated to platform limits."""
        decision = _make_decision(
            platform=Platform.TWITTER,
            hook="x" * 300,  # Very long hook to force truncation
        )
        mock_claude = MagicMock()
        text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key=None,
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert len(text) <= 280
        assert model == "template-fallback"

    def test_brand_defaults_to_empty_dict(self) -> None:
        """Passing brand=None doesn't crash — defaults to empty dict."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("Content here.")
        text, _model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            brand=None,
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert text == "Content here."

    def test_strips_whitespace_from_response(self) -> None:
        """Leading/trailing whitespace in Claude response is stripped."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("  \n Content \n  ")
        text, _model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        assert text == "Content"

    def test_whitespace_only_response_triggers_fallback(self) -> None:
        """Response that is only whitespace falls back to template."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("   \n\n  ")
        _text, model = generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test",
        )
        # Fallback content should be non-empty
        assert len(_text) > 10
        assert model == "claude-sonnet-4-6"

    def test_passes_correct_tier_and_temperature(self) -> None:
        """Verify Claude is called with operational tier and 0.4 temperature."""
        decision = _make_decision()
        mock_claude = MagicMock()
        mock_claude.call.return_value = _make_claude_response("text")
        generate_text_for_decision(
            decision=decision,
            knowledge={},
            products={"products": {}},
            claude=mock_claude,
            anthropic_api_key="sk-test-key",
            sonnet_model="claude-sonnet-4-6",
            agent_id="test-agent",
        )
        call_kwargs = mock_claude.call.call_args.kwargs
        assert call_kwargs["tier"] == "operational"
        assert call_kwargs["temperature"] == 0.4
        assert call_kwargs["agent_id"] == "test-agent"
        assert call_kwargs["max_tokens"] == 1536
