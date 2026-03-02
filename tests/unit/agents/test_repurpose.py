"""Tests for the content repurposing module.

Covers:
  - repurpose_content() with mocked Claude client
  - Fallback behaviour when Claude is unavailable
  - Character limit enforcement per platform
  - Platform rules formatting
  - Edge cases (empty text, single-line text, long text)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from holus.agents.marketing.models import (
    ContentDecision,
    ContentType,
    GeneratedPiece,
    Platform,
)
from holus.agents.marketing.repurpose import (
    CHAR_LIMITS,
    PLATFORM_RULES,
    REPURPOSE_TARGETS,
    _enforce_limit,
    _fallback_adapt,
    _format_rules,
    repurpose_content,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_claude_response(text: str) -> MagicMock:
    """Build a mock Claude API response containing the given text."""
    response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response.content = [text_block]
    response.usage = MagicMock(
        input_tokens=50,
        output_tokens=30,
        cache_read_input_tokens=40,
        cache_creation_input_tokens=10,
    )
    return response


@pytest.fixture()
def mock_claude_client() -> MagicMock:
    """Mock HolusClaudeClient that returns platform-specific adapted text."""
    client = MagicMock()
    client.sonnet_model = "claude-sonnet-4-6"

    def _side_effect(**kwargs: Any) -> MagicMock:
        prompt = kwargs.get("cached_prompt")
        if prompt and hasattr(prompt, "system_prompt"):
            sp = prompt.system_prompt
            if "Twitter" in sp:
                return _make_claude_response("I built Pilaster from scratch. The lesson: start small.")
            if "Instagram" in sp:
                return _make_claude_response(
                    "I built Pilaster from scratch.\n\n"
                    "The lesson? Start small, iterate fast.\n\n"
                    "#AI #Builder #Pilaster"
                )
            if "Threads" in sp:
                return _make_claude_response("Honestly, building Pilaster taught me one thing: start small.")
            if "Facebook" in sp:
                return _make_claude_response(
                    "I built Pilaster from scratch and it changed how I think about AI.\n\n"
                    "The biggest lesson? Start with the smallest testable workflow."
                )
        return _make_claude_response("Adapted content.")

    client.call = MagicMock(side_effect=_side_effect)
    client._cost_log = []
    client.get_costs = MagicMock(return_value=[])
    return client


@pytest.fixture()
def sample_decision() -> ContentDecision:
    """A sample LinkedIn content decision."""
    return ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        content_pillar="builder_stories",
        topic="What I learned building Pilaster",
        hook="I built Pilaster from scratch. Here's what surprised me.",
        framework="confession",
        reasoning="Builder stories demonstrate consulting expertise.",
        priority=1,
        estimated_engagement="high",
        repurpose_notes="Good for Twitter thread.",
    )


@pytest.fixture()
def sample_brand() -> dict[str, Any]:
    """Minimal brand config for testing."""
    return {
        "voice": {
            "archetype": "Builder-Philosopher",
            "summary": "First person, short paragraphs, builder mindset.",
            "tone": ["Confident but honest", "No exclamation marks"],
            "hooks": {"contrarian": "Most people play with AI. A few build with it."},
            "closers": {"question": "What would you build?"},
        },
        "positioning": {
            "one_liner": "I build AI systems that actually work in production.",
        },
    }


SAMPLE_LINKEDIN_TEXT = (
    "I built Pilaster from scratch. Here's what surprised me.\n\n"
    "The first version took 3 weeks. It was terrible.\n\n"
    "But I learned more in those 3 weeks than in 6 months of reading about AI.\n\n"
    "Here's the framework that actually worked:\n\n"
    "1) Start with the smallest testable workflow\n"
    "2) Measure the baseline before optimizing\n"
    "3) Change one variable per iteration\n\n"
    "Most teams skip step 2. That's where the expensive mistakes happen.\n\n"
    "What's the biggest bottleneck in your AI implementation?\n\n"
    "#AI #Builder #Pilaster #Production #Consulting"
)


# ---------------------------------------------------------------------------
# Tests: repurpose_content()
# ---------------------------------------------------------------------------


class TestRepurposeContent:
    """Tests for the main repurpose_content() function."""

    @pytest.mark.asyncio()
    async def test_returns_pieces_for_all_targets(
        self,
        mock_claude_client: MagicMock,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """repurpose_content returns one GeneratedPiece per target platform."""
        pieces = await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=mock_claude_client,
            brand=sample_brand,
            cycle_id="test-cycle",
            piece_index=1,
        )

        assert len(pieces) == len(REPURPOSE_TARGETS)

        platforms = {p.platform for p in pieces}
        assert platforms == set(REPURPOSE_TARGETS)

    @pytest.mark.asyncio()
    async def test_pieces_have_correct_structure(
        self,
        mock_claude_client: MagicMock,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """Each repurposed piece has expected fields and correct decision."""
        pieces = await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=mock_claude_client,
            brand=sample_brand,
            cycle_id="cycle-42",
            piece_index=1,
        )

        for piece in pieces:
            assert isinstance(piece, GeneratedPiece)
            assert piece.decision == sample_decision
            assert piece.status == "pending_review"
            assert piece.model_used == "claude-sonnet-4-6"
            assert "cycle-42-1-" in piece.piece_id
            assert piece.platform.value in piece.piece_id
            assert len(piece.text) > 0

    @pytest.mark.asyncio()
    async def test_custom_targets(
        self,
        mock_claude_client: MagicMock,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """Can override default targets to repurpose to specific platforms."""
        pieces = await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=mock_claude_client,
            brand=sample_brand,
            cycle_id="test-cycle",
            piece_index=1,
            targets=[Platform.TWITTER, Platform.THREADS],
        )

        assert len(pieces) == 2
        platforms = {p.platform for p in pieces}
        assert platforms == {Platform.TWITTER, Platform.THREADS}

    @pytest.mark.asyncio()
    async def test_claude_called_for_each_platform(
        self,
        mock_claude_client: MagicMock,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """Claude client.call is invoked once per target platform."""
        await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=mock_claude_client,
            brand=sample_brand,
            cycle_id="test-cycle",
            piece_index=1,
        )

        assert mock_claude_client.call.call_count == len(REPURPOSE_TARGETS)

    @pytest.mark.asyncio()
    async def test_falls_back_when_claude_fails(
        self,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """When Claude raises an exception, fallback text is used."""
        failing_client = MagicMock()
        failing_client.sonnet_model = "claude-sonnet-4-6"
        failing_client.call = MagicMock(side_effect=RuntimeError("API down"))

        pieces = await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=failing_client,
            brand=sample_brand,
            cycle_id="test-cycle",
            piece_index=1,
        )

        assert len(pieces) == len(REPURPOSE_TARGETS)
        for piece in pieces:
            assert len(piece.text) > 0

    @pytest.mark.asyncio()
    async def test_falls_back_when_claude_returns_empty(
        self,
        sample_decision: ContentDecision,
        sample_brand: dict[str, Any],
    ) -> None:
        """When Claude returns empty text, fallback is used."""
        empty_client = MagicMock()
        empty_client.sonnet_model = "claude-sonnet-4-6"
        empty_client.call = MagicMock(return_value=_make_claude_response(""))

        pieces = await repurpose_content(
            original_text=SAMPLE_LINKEDIN_TEXT,
            decision=sample_decision,
            claude_client=empty_client,
            brand=sample_brand,
            cycle_id="test-cycle",
            piece_index=1,
        )

        assert len(pieces) == len(REPURPOSE_TARGETS)
        for piece in pieces:
            assert len(piece.text) > 0


# ---------------------------------------------------------------------------
# Tests: _enforce_limit()
# ---------------------------------------------------------------------------


class TestEnforceLimit:
    """Tests for character limit enforcement."""

    def test_short_text_unchanged(self) -> None:
        """Text within limit passes through unchanged."""
        text = "Short tweet"
        assert _enforce_limit(text, Platform.TWITTER) == text

    def test_long_text_truncated_with_ellipsis(self) -> None:
        """Text exceeding limit is truncated with '...'."""
        text = "x" * 300
        result = _enforce_limit(text, Platform.TWITTER)
        assert len(result) == 280
        assert result.endswith("...")

    def test_exact_limit_unchanged(self) -> None:
        """Text exactly at the limit passes through."""
        text = "x" * 280
        assert _enforce_limit(text, Platform.TWITTER) == text

    def test_unknown_platform_no_limit(self) -> None:
        """Platform not in CHAR_LIMITS returns text unchanged."""
        text = "x" * 10000
        result = _enforce_limit(text, Platform.YOUTUBE)
        assert result == text

    def test_threads_limit(self) -> None:
        """Threads enforces 500 char limit."""
        text = "x" * 600
        result = _enforce_limit(text, Platform.THREADS)
        assert len(result) == 500
        assert result.endswith("...")

    def test_instagram_limit(self) -> None:
        """Instagram enforces 2200 char limit."""
        text = "x" * 2500
        result = _enforce_limit(text, Platform.INSTAGRAM)
        assert len(result) == 2200
        assert result.endswith("...")


# ---------------------------------------------------------------------------
# Tests: _fallback_adapt()
# ---------------------------------------------------------------------------


class TestFallbackAdapt:
    """Tests for mechanical fallback adaptation."""

    def test_twitter_short_text(self) -> None:
        """Short text that fits in a tweet is returned as first line."""
        result = _fallback_adapt("Short insight.\n\nMore details here.", Platform.TWITTER)
        assert result == "Short insight."

    def test_twitter_long_text_truncated(self) -> None:
        """Long text for Twitter is truncated to 280 with ellipsis."""
        text = "x" * 400
        result = _fallback_adapt(text, Platform.TWITTER)
        assert len(result) <= 280
        assert result.endswith("...")

    def test_instagram_adds_hashtags(self) -> None:
        """Instagram fallback appends basic hashtags."""
        result = _fallback_adapt("Some post content.", Platform.INSTAGRAM)
        assert "#AI" in result
        assert "#Builder" in result

    def test_instagram_trims_long_text(self) -> None:
        """Instagram fallback trims very long text."""
        text = "x" * 3000
        result = _fallback_adapt(text, Platform.INSTAGRAM)
        assert len(result) <= 2200

    def test_threads_first_paragraph(self) -> None:
        """Threads fallback uses just the first paragraph."""
        text = "First paragraph here.\n\nSecond paragraph with more detail.\n\nThird."
        result = _fallback_adapt(text, Platform.THREADS)
        assert result == "First paragraph here."

    def test_threads_long_paragraph_truncated(self) -> None:
        """Threads fallback truncates if first paragraph > 500 chars."""
        text = "x" * 600 + "\n\nSecond paragraph."
        result = _fallback_adapt(text, Platform.THREADS)
        assert len(result) == 500
        assert result.endswith("...")

    def test_facebook_returns_full_text(self) -> None:
        """Facebook fallback returns the full original text."""
        result = _fallback_adapt(SAMPLE_LINKEDIN_TEXT, Platform.FACEBOOK)
        assert result == SAMPLE_LINKEDIN_TEXT

    def test_unknown_platform_returns_original(self) -> None:
        """Unknown platform returns text as-is."""
        result = _fallback_adapt("Hello", Platform.YOUTUBE)
        assert result == "Hello"


# ---------------------------------------------------------------------------
# Tests: _format_rules()
# ---------------------------------------------------------------------------


class TestFormatRules:
    """Tests for platform rules formatting."""

    def test_formats_all_keys(self) -> None:
        """All keys in the rules dict appear in the formatted output."""
        rules = {"max_chars": "280", "style": "Punchy", "adapt": "Extract core insight."}
        result = _format_rules(rules)
        assert "Max chars" in result
        assert "280" in result
        assert "Style" in result
        assert "Punchy" in result

    def test_empty_rules(self) -> None:
        """Empty rules dict returns empty string."""
        assert _format_rules({}) == ""


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_all_targets_have_rules(self) -> None:
        """Every platform in REPURPOSE_TARGETS has an entry in PLATFORM_RULES."""
        for target in REPURPOSE_TARGETS:
            assert target in PLATFORM_RULES, f"Missing rules for {target}"

    def test_all_targets_have_char_limits(self) -> None:
        """Every platform in REPURPOSE_TARGETS has a character limit."""
        for target in REPURPOSE_TARGETS:
            assert target in CHAR_LIMITS, f"Missing char limit for {target}"

    def test_targets_do_not_include_linkedin(self) -> None:
        """LinkedIn is the primary platform and should not be a repurpose target."""
        assert Platform.LINKEDIN not in REPURPOSE_TARGETS

    def test_four_secondary_platforms(self) -> None:
        """There are exactly 4 secondary platforms."""
        assert len(REPURPOSE_TARGETS) == 4
