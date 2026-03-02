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
    "leverage synergies",
    "drive engagement",
    "unlock potential",
    "game-changing",
    "game changing",
    "revolutionary",
    "let's dive in",
    "in today's fast-paced world",
    "here's the thing",
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
