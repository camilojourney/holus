"""Tests for content quality scoring gate."""

from __future__ import annotations

from datetime import UTC, datetime

from holus.agents.marketing.models import ContentDecision, ContentType, GeneratedPiece, Platform
from holus.agents.marketing.quality_score import (
    DEFAULT_ANTI_PATTERN_PHRASES,
    FK_GRADE_THRESHOLD,
    PASS_THRESHOLD,
    PLATFORM_CHAR_LIMITS,
    VALID_PILLARS,
    QualityResult,
    QualityViolation,
    _check_consecutive_same_length,
    _check_flesch_kincaid,
    _check_opening_word_diversity,
    _check_sentence_length_variance,
    _check_single_sentence_paragraphs,
    _count_syllables,
    score_content,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_piece(
    text: str = "6 months building Pilaster taught me 3 lessons about AI deployment with ComfyUI.",
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
                else ("Building Pilaster from scratch revealed this architecture pattern.")
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
        piece = _make_piece(
            text="I spent 6 months building an AI pipeline. 3 things broke along the way."
        )
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


# ---------------------------------------------------------------------------
# Structural AI-detection checks
# ---------------------------------------------------------------------------


class TestStructuralChecks:
    """Tests for the 4 structural AI-detection checks."""

    # -- _check_sentence_length_variance --

    def test_sentence_variance_uniform_triggers(self) -> None:
        # 6 sentences, all ~8 words → very low std dev
        text = (
            "The system handles all the input data. "
            "The model processes every single request. "
            "The pipeline transforms all raw features. "
            "The service returns the final results. "
            "The client receives the full response. "
            "The dashboard displays all the metrics."
        )
        v = _check_sentence_length_variance(text)
        assert v is not None
        assert v.check == "sentence_variance_low"
        assert v.penalty == 15
        assert "std dev" in v.message

    def test_sentence_variance_varied_passes(self) -> None:
        # Sentences with very different lengths → high std dev
        text = (
            "Stop. "
            "This is a radically different approach to building AI systems that actually work in production. "
            "Why? "
            "Because most teams over-engineer their ML pipelines with unnecessary complexity and abstraction layers. "
            "Ship it. "
            "The best architecture is the one your team can debug at 3am when the pager goes off."
        )
        v = _check_sentence_length_variance(text)
        assert v is None

    def test_sentence_variance_too_few_sentences_skips(self) -> None:
        # Only 3 sentences — below the 5-sentence minimum
        text = "First sentence here. Second sentence here. Third sentence here."
        v = _check_sentence_length_variance(text)
        assert v is None

    def test_sentence_variance_empty_text(self) -> None:
        assert _check_sentence_length_variance("") is None

    # -- _check_single_sentence_paragraphs --

    def test_single_sentence_paragraphs_too_few_triggers(self) -> None:
        # 4 paragraphs, 0 single-sentence → 0% < 30%
        text = (
            "The first point is important. It has multiple sentences here.\n\n"
            "The second point builds on that. It also has two sentences.\n\n"
            "Here is the third point. Again with two sentences.\n\n"
            "Finally the fourth point. Two sentences as well."
        )
        v = _check_single_sentence_paragraphs(text, Platform.LINKEDIN)
        assert v is not None
        assert v.check == "few_short_paragraphs"
        assert v.penalty == 10
        assert "30%+" in v.message

    def test_single_sentence_paragraphs_enough_passes(self) -> None:
        # 4 paragraphs, 2 are single-sentence → 50% > 30%
        text = (
            "This stands alone.\n\n"
            "This paragraph has two sentences. Here is the second one.\n\n"
            "Another standalone.\n\n"
            "And a final paragraph with more detail. It elaborates further."
        )
        v = _check_single_sentence_paragraphs(text, Platform.LINKEDIN)
        assert v is None

    def test_single_sentence_paragraphs_non_linkedin_skips(self) -> None:
        # Same violating text but on Twitter — should not fire
        text = (
            "The first point is important. It has multiple sentences.\n\n"
            "The second point builds on that. It also has two sentences.\n\n"
            "Here is the third point. Again with two sentences.\n\n"
            "Finally the fourth point. Two sentences as well."
        )
        v = _check_single_sentence_paragraphs(text, Platform.TWITTER)
        assert v is None

    def test_single_sentence_paragraphs_too_few_paragraphs_skips(self) -> None:
        # Only 2 paragraphs — below the 3-paragraph minimum
        text = "First paragraph with multiple sentences. Two of them.\n\nSecond paragraph here. Also two."
        v = _check_single_sentence_paragraphs(text, Platform.LINKEDIN)
        assert v is None

    # -- _check_opening_word_diversity --

    def test_opening_word_diversity_repetitive_triggers(self) -> None:
        # 4 paragraphs all starting with generic openers
        text = (
            "I built this system from scratch.\n\n"
            "The architecture is clean.\n\n"
            "In production, it handles 10K requests.\n\n"
            "It scales horizontally across regions."
        )
        v = _check_opening_word_diversity(text)
        assert v is not None
        assert v.check == "repetitive_openers"
        assert v.penalty == 10
        assert "repetitive" in v.message.lower()

    def test_opening_word_diversity_varied_passes(self) -> None:
        # 4 paragraphs with diverse openers
        text = (
            "Yesterday we shipped a new feature.\n\n"
            "Most teams struggle with deployment.\n\n"
            "Here is what changed.\n\n"
            "After 6 months, the results speak for themselves."
        )
        v = _check_opening_word_diversity(text)
        assert v is None

    def test_opening_word_diversity_too_few_paragraphs_skips(self) -> None:
        # Only 3 paragraphs — below the 4-paragraph minimum
        text = "I did this.\n\nThe result was good.\n\nIn summary, it worked."
        v = _check_opening_word_diversity(text)
        assert v is None

    def test_opening_word_diversity_empty_text(self) -> None:
        assert _check_opening_word_diversity("") is None

    # -- _check_consecutive_same_length --

    def test_consecutive_same_length_triggers(self) -> None:
        # 3 consecutive sentences each with 7 words (within +/-2)
        text = (
            "The system handles all the requests well. "
            "The model processes every input it gets. "
            "The pipeline transforms raw data into features."
        )
        v = _check_consecutive_same_length(text)
        assert v is not None
        assert v.check == "mechanical_rhythm"
        assert v.penalty == 10
        assert "mechanical rhythm" in v.message

    def test_consecutive_same_length_varied_passes(self) -> None:
        # 3 sentences with very different lengths
        text = (
            "Stop. "
            "The entire ML pipeline was rebuilt from the ground up over six months of intensive work. "
            "It works now."
        )
        v = _check_consecutive_same_length(text)
        assert v is None

    def test_consecutive_same_length_too_few_sentences_skips(self) -> None:
        # Only 2 sentences
        text = "First sentence here. Second sentence here."
        v = _check_consecutive_same_length(text)
        assert v is None

    def test_consecutive_same_length_empty_text(self) -> None:
        assert _check_consecutive_same_length("") is None

    # -- Integration: default _make_piece still passes --

    def test_default_piece_unaffected_by_structural_checks(self) -> None:
        """Ensure the default test piece still scores 100 with structural checks."""
        piece = _make_piece()
        result = score_content(piece)
        assert result.passed is True
        assert result.score == 100
        assert result.violations == []


# ---------------------------------------------------------------------------
# score_content — LinkedIn "I" opening
# ---------------------------------------------------------------------------


class TestLinkedinIOpening:
    def test_linkedin_starting_with_i_fails(self) -> None:
        piece = _make_piece(
            text="I've shipped 3 production AI systems. The demo never failed.",
            platform=Platform.LINKEDIN,
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "linkedin_i_opening"]
        assert len(violations) == 1
        assert violations[0].penalty == 15

    def test_linkedin_starting_with_i_space_fails(self) -> None:
        piece = _make_piece(
            text="I built Pilaster from scratch. Here's what happened.",
            platform=Platform.LINKEDIN,
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "linkedin_i_opening"]
        assert len(violations) == 1

    def test_linkedin_not_starting_with_i_passes(self) -> None:
        piece = _make_piece(
            text="75% of AI pilots never reach production. Here's why.",
            platform=Platform.LINKEDIN,
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "linkedin_i_opening"]
        assert len(violations) == 0

    def test_non_linkedin_starting_with_i_passes(self) -> None:
        """The 'I' opening check only applies to LinkedIn."""
        piece = _make_piece(
            text="I've shipped 3 production AI systems.",
            platform=Platform.INSTAGRAM,
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "linkedin_i_opening"]
        assert len(violations) == 0

    def test_linkedin_i_in_middle_passes(self) -> None:
        piece = _make_piece(
            text="Most teams skip this layer. I learned that the hard way.",
            platform=Platform.LINKEDIN,
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "linkedin_i_opening"]
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# Expanded AI slop phrases
# ---------------------------------------------------------------------------


class TestExpandedAiSlopPhrases:
    """Tests for the 30 new AI-giveaway phrases added in Cycle 80."""

    def test_detects_its_important_to_note(self) -> None:
        piece = _make_piece(
            text="It's important to note that AI pipelines fail silently in production."
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("it's important to note" in v.message.lower() for v in violations)

    def test_detects_that_being_said(self) -> None:
        piece = _make_piece(
            text="Pilaster handles 10K requests daily. That being said, scaling is tricky."
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("that being said" in v.message.lower() for v in violations)

    def test_detects_in_the_realm_of(self) -> None:
        piece = _make_piece(text="In the realm of ML deployment, monitoring matters most.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("in the realm of" in v.message.lower() for v in violations)

    def test_detects_truly_remarkable(self) -> None:
        piece = _make_piece(text="The results were truly remarkable after switching backends.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("truly remarkable" in v.message.lower() for v in violations)

    def test_detects_paradigm_shift(self) -> None:
        piece = _make_piece(text="This is a paradigm shift in how teams deploy models.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("paradigm shift" in v.message.lower() for v in violations)

    def test_detects_a_testament_to(self) -> None:
        piece = _make_piece(
            text="This is a testament to the team's dedication to quality engineering."
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("a testament to" in v.message.lower() for v in violations)

    def test_detects_when_it_comes_to(self) -> None:
        piece = _make_piece(text="When it comes to AI deployment, most teams get it wrong.")
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert any("when it comes to" in v.message.lower() for v in violations)

    def test_total_anti_pattern_count_above_60(self) -> None:
        """Ensure we have at least 60 anti-pattern phrases after expansion."""
        assert len(DEFAULT_ANTI_PATTERN_PHRASES) >= 60

    def test_clean_builder_text_no_slop(self) -> None:
        """Real builder content should pass without triggering new slop phrases."""
        piece = _make_piece(
            text=(
                "6 months ago our image pipeline crashed every 3 hours.\n"
                "We rewrote the retry logic from scratch.\n"
                "Downtime went from 47 minutes/week to zero.\n"
                "The fix was 12 lines of Python."
            )
        )
        result = score_content(piece)
        violations = [v for v in result.violations if v.check == "anti_pattern"]
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# Syllable counting helper
# ---------------------------------------------------------------------------


class TestSyllableCounter:
    def test_one_syllable_words(self) -> None:
        assert _count_syllables("cat") == 1
        assert _count_syllables("the") == 1
        assert _count_syllables("dog") == 1

    def test_two_syllable_words(self) -> None:
        assert _count_syllables("happy") == 2
        assert _count_syllables("model") == 2

    def test_three_syllable_words(self) -> None:
        assert _count_syllables("beautiful") == 3
        assert _count_syllables("customer") == 3

    def test_silent_e(self) -> None:
        # "make" should be 1 syllable, not 2
        assert _count_syllables("make") == 1
        # "came" → 1 syllable (silent e trims vowel group)
        assert _count_syllables("came") == 1

    def test_empty_string(self) -> None:
        assert _count_syllables("") == 0

    def test_strips_punctuation(self) -> None:
        assert _count_syllables("hello,") == 2
        assert _count_syllables("world!") == 1


# ---------------------------------------------------------------------------
# Flesch-Kincaid grade level check
# ---------------------------------------------------------------------------


class TestFleschKincaid:
    def test_simple_text_passes(self) -> None:
        """Short sentences, simple words → low FK grade."""
        text = (
            "We built a system. It processes images. "
            "The API is fast. Users love it. Teams ship faster."
        )
        v = _check_flesch_kincaid(text)
        assert v is None

    def test_academic_text_fails(self) -> None:
        """Long sentences with polysyllabic words → high FK grade."""
        text = (
            "The implementation of sophisticated computational infrastructure "
            "necessitates comprehensive understanding of distributed architectures. "
            "Furthermore, the characterization of performance optimization opportunities "
            "requires meticulous examination of heterogeneous parallelization strategies. "
            "Consequently, the establishment of reproducible experimentation methodologies "
            "facilitates systematic identification of architectural bottlenecks."
        )
        v = _check_flesch_kincaid(text)
        assert v is not None
        assert v.check == "flesch_kincaid_high"
        assert v.penalty == 15

    def test_too_few_sentences_skips(self) -> None:
        """Less than 3 sentences → skip check."""
        text = "Short text. Only two sentences."
        v = _check_flesch_kincaid(text)
        assert v is None

    def test_too_few_words_skips(self) -> None:
        """Less than 10 words → skip check."""
        text = "One. Two. Three."
        v = _check_flesch_kincaid(text)
        assert v is None

    def test_empty_text_skips(self) -> None:
        v = _check_flesch_kincaid("")
        assert v is None

    def test_threshold_constant(self) -> None:
        assert FK_GRADE_THRESHOLD == 12.0

    def test_integrated_in_score_content(self) -> None:
        """Academic text triggers flesch_kincaid_high in full scoring pipeline."""
        piece = _make_piece(
            text=(
                "The implementation of sophisticated computational infrastructure "
                "necessitates comprehensive understanding of distributed architectures. "
                "Furthermore, the characterization of performance optimization opportunities "
                "requires meticulous examination of heterogeneous parallelization strategies. "
                "Consequently, the establishment of reproducible experimentation methodologies "
                "facilitates systematic identification of architectural bottlenecks."
            )
        )
        result = score_content(piece)
        fk_violations = [v for v in result.violations if v.check == "flesch_kincaid_high"]
        assert len(fk_violations) == 1
