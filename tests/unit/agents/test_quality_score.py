"""Tests for content quality scoring gate."""

from __future__ import annotations

from datetime import UTC, datetime

from holus.agents.marketing.models import ContentDecision, ContentType, GeneratedPiece, Platform
from holus.agents.marketing.quality_score import (
    DEFAULT_ANTI_PATTERN_PHRASES,
    PASS_THRESHOLD,
    PLATFORM_CHAR_LIMITS,
    VALID_PILLARS,
    QualityResult,
    QualityViolation,
    score_content,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_piece(
    text: str = "I built Pilaster from scratch. Here's what I learned about AI deployment.",
    platform: Platform = Platform.LINKEDIN,
    content_pillar: str = "builder_stories",
    hook: str = "I built Pilaster from scratch.",
) -> GeneratedPiece:
    return GeneratedPiece(
        piece_id="test-1-abc12345",
        decision=ContentDecision(
            product="pilaster",
            platform=platform,
            content_type=ContentType.TUTORIAL,
            content_pillar=content_pillar,
            topic="Building AI systems",
            hook=hook,
            reasoning="Authority building",
        ),
        text=text,
        platform=platform,
        generated_at=datetime.now(UTC),
        model_used="sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# QualityViolation / QualityResult
# ---------------------------------------------------------------------------


class TestQualityViolation:
    def test_to_dict(self) -> None:
        v = QualityViolation(check="test", message="msg", penalty=10)
        d = v.to_dict()
        assert d == {"check": "test", "message": "msg", "penalty": 10}

    def test_repr(self) -> None:
        v = QualityViolation(check="test", message="msg", penalty=10)
        assert "test" in repr(v)
        assert "10" in repr(v)


class TestQualityResult:
    def test_pass_above_threshold(self) -> None:
        r = QualityResult(score=80, violations=[])
        assert r.passed is True
        assert r.score == 80

    def test_fail_below_threshold(self) -> None:
        v = QualityViolation(check="x", message="x", penalty=50)
        r = QualityResult(score=50, violations=[v])
        assert r.passed is False

    def test_score_clamped_to_0_100(self) -> None:
        r = QualityResult(score=-20, violations=[])
        assert r.score == 0

        r2 = QualityResult(score=150, violations=[])
        assert r2.score == 100

    def test_to_dict(self) -> None:
        r = QualityResult(score=90, violations=[])
        d = r.to_dict()
        assert d["score"] == 90
        assert d["passed"] is True
        assert d["violations"] == []

    def test_threshold_boundary(self) -> None:
        r = QualityResult(score=PASS_THRESHOLD, violations=[])
        assert r.passed is True

        r2 = QualityResult(score=PASS_THRESHOLD - 1, violations=[])
        assert r2.passed is False


# ---------------------------------------------------------------------------
# score_content — clean content
# ---------------------------------------------------------------------------


class TestScoreContentClean:
    def test_good_content_passes(self) -> None:
        piece = _make_piece()
        result = score_content(piece)
        assert result.passed is True
        assert result.score == 100
        assert result.violations == []

    def test_good_content_all_platforms(self) -> None:
        for platform in [Platform.LINKEDIN, Platform.TWITTER, Platform.INSTAGRAM]:
            text = (
                "Short hook that works."
                if platform == Platform.TWITTER
                else ("I built Pilaster from scratch. Here's the architecture behind it.")
            )
            piece = _make_piece(text=text, platform=platform)
            result = score_content(piece)
            assert result.passed is True, f"Failed for {platform}"


# ---------------------------------------------------------------------------
# score_content — character limits
# ---------------------------------------------------------------------------


class TestCharLimits:
    def test_twitter_over_limit(self) -> None:
        text = "x" * 300
        piece = _make_piece(text=text, platform=Platform.TWITTER)
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "char_limit"]
        assert len(violations) == 1
        assert "280" in violations[0].message

    def test_linkedin_under_limit(self) -> None:
        text = "x" * 2999
        piece = _make_piece(text=text, platform=Platform.LINKEDIN)
        result = score_content(piece)
        char_violations = [v for v in result.violations if v.check == "char_limit"]
        assert len(char_violations) == 0

    def test_linkedin_over_limit(self) -> None:
        text = "x" * 3100
        piece = _make_piece(text=text, platform=Platform.LINKEDIN)
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "char_limit"]
        assert len(violations) == 1

    def test_threads_at_exact_limit(self) -> None:
        text = "x" * 500
        piece = _make_piece(text=text, platform=Platform.THREADS)
        result = score_content(piece)
        char_violations = [v for v in result.violations if v.check == "char_limit"]
        assert len(char_violations) == 0

    def test_unknown_platform_no_limit(self) -> None:
        piece = _make_piece(text="x" * 10000, platform=Platform.YOUTUBE)
        result = score_content(piece)
        char_violations = [v for v in result.violations if v.check == "char_limit"]
        assert len(char_violations) == 0


# ---------------------------------------------------------------------------
# score_content — anti-pattern phrases
# ---------------------------------------------------------------------------


class TestAntiPatternPhrases:
    def test_detects_leverage_synergies(self) -> None:
        piece = _make_piece(text="We need to leverage synergies in AI deployment.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) >= 1
        assert any("leverage synergies" in v.message for v in violations)

    def test_detects_case_insensitive(self) -> None:
        piece = _make_piece(text="This is GAME-CHANGING technology for everyone.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) >= 1

    def test_detects_lets_dive_in(self) -> None:
        piece = _make_piece(text="Let's dive in! Here's how AI works.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("dive in" in v.message.lower() for v in violations)

    def test_detects_multiple_anti_patterns(self) -> None:
        piece = _make_piece(
            text="Let's dive in! This is game-changing. Furthermore, it unlocks potential."
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) >= 3

    def test_clean_text_no_anti_patterns(self) -> None:
        piece = _make_piece(text="I spent 6 months building an AI pipeline. Here's what broke.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) == 0

    def test_extra_brand_phrases_merged(self) -> None:
        piece = _make_piece(text="This is a paradigm shift in the AI industry.")
        result = score_content(piece, brand_anti_patterns=["paradigm shift"])
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) >= 1
        assert any("paradigm shift" in v.message for v in violations)


# ---------------------------------------------------------------------------
# score_content — content anti-patterns (forbidden topics)
# ---------------------------------------------------------------------------


class TestContentAntiPatterns:
    def test_detects_trading_mention(self) -> None:
        piece = _make_piece(text="My trading system made 50% returns this quarter.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "content_anti_pattern"]
        assert len(violations) >= 1

    def test_detects_pythia(self) -> None:
        piece = _make_piece(text="I also built pythia for market prediction.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "content_anti_pattern"]
        assert len(violations) >= 1

    def test_detects_financial_advice(self) -> None:
        piece = _make_piece(text="Here's my financial advice for investing in AI stocks.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "content_anti_pattern"]
        assert len(violations) >= 1

    def test_high_penalty_for_forbidden_topic(self) -> None:
        piece = _make_piece(text="My milo-to-the-moon system for crypto trading works great.")
        result = score_content(piece)
        content_violations = [v for v in result.violations if v.check == "content_anti_pattern"]
        assert len(content_violations) >= 1
        assert all(v.penalty == 50 for v in content_violations)


# ---------------------------------------------------------------------------
# score_content — hook presence
# ---------------------------------------------------------------------------


class TestHookPresence:
    def test_empty_content_fails(self) -> None:
        piece = _make_piece(text="")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "empty_content"]
        assert len(violations) == 1
        assert violations[0].penalty == 100

    def test_whitespace_only_fails(self) -> None:
        piece = _make_piece(text="   \n  \n  ")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "empty_content"]
        assert len(violations) == 1

    def test_very_short_first_line_fails(self) -> None:
        piece = _make_piece(text="Hey.\n\nHere is the actual content that follows.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "weak_hook"]
        assert len(violations) == 1

    def test_good_hook_passes(self) -> None:
        piece = _make_piece(
            text="I spent 200 hours building an AI image platform. Here's what broke.\n\nThe details..."
        )
        result = score_content(piece)
        hook_violations = [
            v for v in result.violations if v.check in ("empty_content", "weak_hook")
        ]
        assert len(hook_violations) == 0


# ---------------------------------------------------------------------------
# score_content — pillar assignment
# ---------------------------------------------------------------------------


class TestPillarAssignment:
    def test_valid_pillar_passes(self) -> None:
        for pillar in VALID_PILLARS:
            piece = _make_piece(content_pillar=pillar)
            result = score_content(piece)
            violations = [v for v in result.violations if v.check == "missing_pillar"]
            assert len(violations) == 0, f"Failed for pillar {pillar}"

    def test_empty_pillar_fails(self) -> None:
        piece = _make_piece(content_pillar="")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "missing_pillar"]
        assert len(violations) == 1

    def test_invalid_pillar_fails(self) -> None:
        piece = _make_piece(content_pillar="random_stuff")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "missing_pillar"]
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# score_content — exclamation density
# ---------------------------------------------------------------------------


class TestExclamationDensity:
    def test_no_exclamations_passes(self) -> None:
        piece = _make_piece(text="I built this system. It works well. Here is the proof.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "exclamation_density"]
        assert len(violations) == 0

    def test_excessive_exclamations_fails(self) -> None:
        # 10 exclamation marks in ~50 chars = 20% ratio
        piece = _make_piece(
            text="Wow! Amazing! Incredible! Great! Super! Best! Top! Nice! Cool! Yes!"
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "exclamation_density"]
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# score_content — emoji density
# ---------------------------------------------------------------------------


class TestEmojiDensity:
    def test_no_emoji_passes(self) -> None:
        piece = _make_piece(text="Clean professional content without any emojis at all.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "emoji_density"]
        assert len(violations) == 0

    def test_heavy_emoji_fails(self) -> None:
        piece = _make_piece(text="\U0001f680\U0001f525\U0001f4af\U0001f389\U0001f3af short")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "emoji_density"]
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# score_content — combined scoring
# ---------------------------------------------------------------------------


class TestCombinedScoring:
    def test_multiple_violations_reduce_score(self) -> None:
        # Anti-pattern phrase (15) + weak hook (15) + invalid pillar (10) = 40 penalty
        piece = _make_piece(
            text="Hey.\n\nLet's dive in! This is game-changing.",
            content_pillar="invalid",
        )
        result = score_content(piece)
        assert result.score < 100
        assert len(result.violations) >= 3

    def test_fatal_violation_fails(self) -> None:
        piece = _make_piece(text="")
        result = score_content(piece)
        assert result.passed is False
        assert result.score == 0

    def test_content_anti_pattern_likely_fails(self) -> None:
        # Content anti-pattern has 50 penalty — one is enough to hurt
        piece = _make_piece(text="Check out my pythia trading system for crypto.")
        result = score_content(piece)
        assert result.score <= 50


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    def test_platform_limits_match_known_values(self) -> None:
        assert PLATFORM_CHAR_LIMITS[Platform.TWITTER] == 280
        assert PLATFORM_CHAR_LIMITS[Platform.LINKEDIN] == 3000
        assert PLATFORM_CHAR_LIMITS[Platform.INSTAGRAM] == 2200
        assert PLATFORM_CHAR_LIMITS[Platform.THREADS] == 500

    def test_default_anti_patterns_non_empty(self) -> None:
        assert len(DEFAULT_ANTI_PATTERN_PHRASES) > 5

    def test_valid_pillars_has_five(self) -> None:
        assert len(VALID_PILLARS) == 5

    def test_pass_threshold_reasonable(self) -> None:
        assert 40 <= PASS_THRESHOLD <= 80
