"""Content quality scoring gate.

Evaluates generated content against brand anti-patterns, platform limits,
and structural requirements before it enters the review queue.
Content below the threshold is auto-rejected and logged, not queued.
"""

from __future__ import annotations

import re

import structlog

from holus.agents.marketing.models import GeneratedPiece, Platform

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Platform character limits (canonical source — used for scoring)
# ---------------------------------------------------------------------------

PLATFORM_CHAR_LIMITS: dict[Platform, int] = {
    Platform.TWITTER: 280,
    Platform.LINKEDIN: 3000,
    Platform.INSTAGRAM: 2200,
    Platform.THREADS: 500,
    Platform.FACEBOOK: 63206,
}

# ---------------------------------------------------------------------------
# Anti-pattern phrases to detect in generated text (case-insensitive)
# These are the *detectable* subset of brand.yaml anti_patterns.language —
# style anti-patterns (walls of text, passive voice) need structural checks.
# ---------------------------------------------------------------------------

DEFAULT_ANTI_PATTERN_PHRASES: list[str] = [
    # Corporate jargon
    "leverage synergies",
    "drive engagement",
    "unlock potential",
    "game-changing",
    "game changing",
    "game-changer",
    "game changer",
    "revolutionary",
    # AI-typical openers and transitions (12-34x natural frequency)
    "let's dive in",
    "in today's fast-paced world",
    "here's the thing",
    "let that sink in",
    "delve",
    "in today's world",
    "in today's landscape",
    "it's worth noting",
    "at the end of the day",
    "it goes without saying",
    "needless to say",
    "without further ado",
    "first and foremost",
    "last but not least",
    "the reality is",
    "the truth is",
    "to be honest",
    "if you're like me",
    "let me be clear",
    # AI-typical hooks (fake engagement bait)
    "imagine this",
    "picture this",
    "buckle up",
    "spoiler alert",
    "hot take",
    "unpopular opinion",
    "here's why",
    "here's what",
    # Filler / hedging
    "great question",
    "furthermore",
    "additionally",
    "moreover",
]

# Content anti-patterns (forbidden topics)
CONTENT_ANTI_PATTERNS: list[str] = [
    "financial advice",
    "investment decision",
    "trading",
    "pythia",
    "milo-to-the-moon",
    "milo to the moon",
]

# Valid content pillars
VALID_PILLARS: set[str] = {
    "builder_stories",
    "ai_frameworks",
    "industry_analysis",
    "results_proof",
    "contrarian_takes",
}

# Scoring thresholds
PASS_THRESHOLD: int = 60
MAX_EXCLAMATION_RATIO: float = 0.03  # max 3% of chars can be !
MAX_EMOJI_RATIO: float = 0.02  # max 2% of chars


# ---------------------------------------------------------------------------
# Quality result
# ---------------------------------------------------------------------------


class QualityViolation:
    """A single quality check failure."""

    __slots__ = ("check", "message", "penalty")

    def __init__(self, check: str, message: str, penalty: int) -> None:
        self.check = check
        self.message = message
        self.penalty = penalty

    def to_dict(self) -> dict[str, str | int]:
        return {"check": self.check, "message": self.message, "penalty": self.penalty}

    def __repr__(self) -> str:
        return f"QualityViolation({self.check!r}, penalty={self.penalty})"


class QualityResult:
    """Result of scoring a content piece."""

    __slots__ = ("passed", "score", "violations")

    def __init__(self, score: int, violations: list[QualityViolation]) -> None:
        self.score = max(0, min(100, score))
        self.violations = violations
        self.passed = self.score >= PASS_THRESHOLD

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
        }


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"  # dingbats
    "\U000024c2-\U0001f251"
    "]+",
    flags=re.UNICODE,
)


def _check_char_limit(text: str, platform: Platform) -> QualityViolation | None:
    limit = PLATFORM_CHAR_LIMITS.get(platform)
    if limit is None:
        return None
    if len(text) > limit:
        over = len(text) - limit
        return QualityViolation(
            check="char_limit",
            message=f"Exceeds {platform.value} limit by {over} chars ({len(text)}/{limit})",
            penalty=30,
        )
    return None


def _check_anti_pattern_phrases(
    text: str, extra_phrases: list[str] | None = None
) -> list[QualityViolation]:
    violations: list[QualityViolation] = []
    lower = text.lower()
    phrases = DEFAULT_ANTI_PATTERN_PHRASES + (extra_phrases or [])
    for phrase in phrases:
        if phrase.lower() in lower:
            violations.append(
                QualityViolation(
                    check="anti_pattern",
                    message=f"Contains anti-pattern phrase: '{phrase}'",
                    penalty=15,
                )
            )
    return violations


def _check_content_anti_patterns(text: str) -> list[QualityViolation]:
    violations: list[QualityViolation] = []
    lower = text.lower()
    for phrase in CONTENT_ANTI_PATTERNS:
        if phrase in lower:
            violations.append(
                QualityViolation(
                    check="content_anti_pattern",
                    message=f"Contains forbidden topic: '{phrase}'",
                    penalty=50,
                )
            )
    return violations


def _check_hook_present(piece: GeneratedPiece) -> QualityViolation | None:
    text = piece.text.strip()
    if not text:
        return QualityViolation(check="empty_content", message="Content text is empty", penalty=100)
    first_line = text.split("\n")[0].strip()
    if len(first_line) < 10:
        return QualityViolation(
            check="weak_hook",
            message=f"First line too short for a hook ({len(first_line)} chars)",
            penalty=15,
        )
    return None


def _check_pillar_assigned(piece: GeneratedPiece) -> QualityViolation | None:
    pillar = piece.decision.content_pillar
    if not pillar or pillar not in VALID_PILLARS:
        return QualityViolation(
            check="missing_pillar",
            message=f"Invalid or missing content pillar: '{pillar}'",
            penalty=10,
        )
    return None


def _check_exclamation_density(text: str) -> QualityViolation | None:
    if not text:
        return None
    count = text.count("!")
    ratio = count / len(text)
    if ratio > MAX_EXCLAMATION_RATIO:
        return QualityViolation(
            check="exclamation_density",
            message=f"Too many exclamation marks ({count} in {len(text)} chars)",
            penalty=10,
        )
    return None


def _check_emoji_density(text: str) -> QualityViolation | None:
    if not text:
        return None
    emoji_chars = _EMOJI_RE.findall(text)
    total_emoji = sum(len(e) for e in emoji_chars)
    ratio = total_emoji / len(text)
    if ratio > MAX_EMOJI_RATIO:
        return QualityViolation(
            check="emoji_density",
            message=f"Too many emojis ({total_emoji} emoji chars in {len(text)} chars)",
            penalty=10,
        )
    return None


_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_NUMBER_RE = re.compile(r"\d+")
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+\b")


def _check_readability(text: str) -> QualityViolation | None:
    """Check average sentence length for mobile readability.

    Too long (>25 words/sentence) means dense, hard-to-scan prose.
    Too short (<5 words/sentence) means choppy lists that lack substance.
    """
    if not text:
        return None
    # Split on sentence-ending punctuation and filter empty fragments
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        return None
    total_words = sum(len(s.split()) for s in sentences)
    avg_words = total_words / len(sentences)
    if avg_words > 25:
        return QualityViolation(
            check="readability_dense",
            message=(
                f"Avg {avg_words:.1f} words/sentence — too dense for mobile "
                f"({len(sentences)} sentences, {total_words} words)"
            ),
            penalty=15,
        )
    if avg_words < 5:
        return QualityViolation(
            check="readability_choppy",
            message=(
                f"Avg {avg_words:.1f} words/sentence — too choppy/listy "
                f"({len(sentences)} sentences, {total_words} words)"
            ),
            penalty=10,
        )
    return None


def _check_specificity(text: str) -> QualityViolation | None:
    """Check that content contains concrete evidence (numbers, named entities).

    Generic content with zero numbers and zero proper nouns reads as vague filler.
    Content with only a single number has weak specificity.
    """
    if not text:
        return None
    number_count = len(_NUMBER_RE.findall(text))
    proper_noun_count = len(_PROPER_NOUN_RE.findall(text))
    if number_count == 0 and proper_noun_count == 0:
        return QualityViolation(
            check="specificity_generic",
            message=(
                "No numbers and no proper nouns found — content is generic with no evidence"
            ),
            penalty=20,
        )
    if number_count == 1 and proper_noun_count == 0:
        return QualityViolation(
            check="specificity_weak",
            message=(
                f"Only 1 number and no proper nouns — weak specificity "
                f"(numbers: {number_count}, proper nouns: {proper_noun_count})"
            ),
            penalty=5,
        )
    return None


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------


def score_content(
    piece: GeneratedPiece,
    brand_anti_patterns: list[str] | None = None,
) -> QualityResult:
    """Score a generated content piece for quality.

    Runs all checks and returns a QualityResult with score (0-100) and violations.
    Content starts at 100 and loses points per violation.

    Args:
        piece: The generated content piece to score.
        brand_anti_patterns: Extra anti-pattern phrases from brand.yaml
            (merged with defaults).

    Returns:
        QualityResult with score, violations, and pass/fail status.
    """
    violations: list[QualityViolation] = []
    text = piece.text

    # Character limit
    v = _check_char_limit(text, piece.platform)
    if v:
        violations.append(v)

    # Anti-pattern language
    violations.extend(_check_anti_pattern_phrases(text, brand_anti_patterns))

    # Forbidden content topics
    violations.extend(_check_content_anti_patterns(text))

    # Hook present (first line quality)
    v = _check_hook_present(piece)
    if v:
        violations.append(v)

    # Content pillar assigned
    v = _check_pillar_assigned(piece)
    if v:
        violations.append(v)

    # Exclamation mark density
    v = _check_exclamation_density(text)
    if v:
        violations.append(v)

    # Emoji density
    v = _check_emoji_density(text)
    if v:
        violations.append(v)

    # Readability (sentence length)
    v = _check_readability(text)
    if v:
        violations.append(v)

    # Specificity (numbers, proper nouns)
    v = _check_specificity(text)
    if v:
        violations.append(v)

    # Calculate score
    total_penalty = sum(v.penalty for v in violations)
    score = max(0, 100 - total_penalty)

    result = QualityResult(score=score, violations=violations)

    logger.info(
        "quality_score",
        piece_id=piece.piece_id,
        platform=piece.platform.value,
        score=result.score,
        passed=result.passed,
        violation_count=len(violations),
    )

    return result
