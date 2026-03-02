"""Tests for the review CLI quality score integration."""

from __future__ import annotations

from datetime import UTC, datetime

from holus.agents.marketing.content_queue import QueuedContent
from holus.agents.marketing.models import Platform
from holus.agents.marketing.quality_score import PASS_THRESHOLD
from holus.agents.marketing.review import _queued_to_generated, _render_quality_panel, _score_color

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_queued(
    *,
    text: str = "I built an AI system that cut deployment time by 60%. Here is what I learned.",
    platform: str = "linkedin",
    product: str = "pilaster",
    content_type: str = "tutorial",
    topic: str = "AI deployment speed",
    reasoning: str = "Builder story demonstrates expertise.",
) -> QueuedContent:
    return QueuedContent(
        piece_id="test1234",
        product=product,
        platform=platform,
        content_type=content_type,
        topic=topic,
        text=text,
        reasoning=reasoning,
        generated_at=datetime(2026, 3, 2, 12, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# _queued_to_generated
# ---------------------------------------------------------------------------


class TestQueuedToGenerated:
    def test_basic_conversion(self) -> None:
        queued = _make_queued()
        piece = _queued_to_generated(queued)

        assert piece.piece_id == "test1234"
        assert piece.platform == Platform.LINKEDIN
        assert piece.text == queued.text
        assert piece.decision.product == "pilaster"
        assert piece.decision.topic == "AI deployment speed"
        assert piece.model_used == "unknown"

    def test_invalid_platform_falls_back_to_linkedin(self) -> None:
        queued = _make_queued(platform="myspace")
        piece = _queued_to_generated(queued)
        assert piece.platform == Platform.LINKEDIN

    def test_invalid_content_type_falls_back_to_tutorial(self) -> None:
        queued = _make_queued(content_type="podcast")
        piece = _queued_to_generated(queued)
        assert piece.decision.content_type.value == "tutorial"

    def test_all_valid_platforms(self) -> None:
        for platform in ["linkedin", "twitter", "instagram", "threads", "facebook"]:
            queued = _make_queued(platform=platform)
            piece = _queued_to_generated(queued)
            assert piece.platform.value == platform


# ---------------------------------------------------------------------------
# _score_color
# ---------------------------------------------------------------------------


class TestScoreColor:
    def test_high_score_green(self) -> None:
        assert _score_color(100) == "green"
        assert _score_color(80) == "green"

    def test_medium_score_yellow(self) -> None:
        assert _score_color(79) == "yellow"
        assert _score_color(60) == "yellow"

    def test_low_score_red(self) -> None:
        assert _score_color(59) == "red"
        assert _score_color(0) == "red"


# ---------------------------------------------------------------------------
# _render_quality_panel
# ---------------------------------------------------------------------------


class TestRenderQualityPanel:
    def test_passing_content_renders_panel(self) -> None:
        queued = _make_queued()
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        panel = _render_quality_panel(result, queued.text, piece.platform)

        # Panel is a rich Panel object
        assert panel.title is not None
        # Renderable text contains the score
        rendered = str(panel.renderable)
        assert "/100" in rendered

    def test_failing_content_shows_violations(self) -> None:
        # Text with anti-pattern and forbidden topic
        bad_text = "Let's dive in to this game-changing trading platform!"
        queued = _make_queued(text=bad_text)
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        assert not result.passed

        panel = _render_quality_panel(result, bad_text, piece.platform)
        rendered = str(panel.renderable)
        assert "Violations" in rendered

    def test_char_limit_bar_for_twitter(self) -> None:
        short_text = "Quick AI tip: automate your tests."
        queued = _make_queued(text=short_text, platform="twitter")
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        panel = _render_quality_panel(result, short_text, piece.platform)
        rendered = str(panel.renderable)
        assert "/280" in rendered  # Twitter char limit shown

    def test_no_limit_platform(self) -> None:
        queued = _make_queued(platform="tiktok")
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        panel = _render_quality_panel(result, queued.text, piece.platform)
        rendered = str(panel.renderable)
        assert "no limit" in rendered


# ---------------------------------------------------------------------------
# Integration: full review flow with quality scoring
# ---------------------------------------------------------------------------


class TestReviewQualityIntegration:
    def test_good_content_scores_high(self) -> None:
        queued = _make_queued(
            text="I built an AI system that cut deployment time by 60%.\n\nHere are the 3 key decisions that made it work.\n\n1. Start with the simplest model\n2. Measure everything\n3. Ship daily",
        )
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        assert result.passed
        assert result.score >= PASS_THRESHOLD

    def test_bad_content_scores_low(self) -> None:
        queued = _make_queued(
            text="Let's dive in to this game-changing revolutionary tool! Furthermore, in today's fast-paced world, trading is the key to financial advice success!",
        )
        piece = _queued_to_generated(queued)
        from holus.agents.marketing.quality_score import score_content

        result = score_content(piece)
        assert not result.passed
        assert result.score < PASS_THRESHOLD
