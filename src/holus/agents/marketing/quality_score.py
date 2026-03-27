"""Content quality scoring gate.

Evaluates generated content against brand anti-patterns, platform limits,
and structural requirements before it enters the review queue.
Content below the threshold is auto-rejected and logged, not queued.
"""

from __future__ import annotations

import re
import statistics

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
    # AI slop — overused transitional filler (ChatGPT / Claude signature phrases)
    "it's important to note",
    "it's crucial to",
    "it's essential to",
    "it's no secret that",
    "it's not just about",
    "that said",
    "that being said",
    "having said that",
    "in a nutshell",
    "at its core",
    "when it comes to",
    "in the world of",
    "in the realm of",
    "on the other hand",
    "as a matter of fact",
    "in this day and age",
    # AI slop — superlative padding
    "incredibly powerful",
    "truly remarkable",
    "absolutely essential",
    "incredibly important",
    "simply put",
    "the bottom line",
    "make no mistake",
    # AI slop — fake depth / pseudo-insight
    "think about it",
    "the landscape is shifting",
    "the landscape has changed",
    "paradigm shift",
    "a testament to",
    "the key takeaway",
    "the takeaway here",
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
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)

# Flesch-Kincaid threshold: grade level > 12 means too academic for social media
FK_GRADE_THRESHOLD: float = 12.0


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word using vowel-group heuristic."""
    word = word.lower().strip(".,;:!?\"'()-")
    if not word:
        return 0
    count = len(_VOWEL_GROUP_RE.findall(word))
    # Silent 'e' at end
    if word.endswith("e") and count > 1:
        count -= 1
    # Words like "the", "me" — at least 1 syllable
    return max(count, 1)


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


def _check_flesch_kincaid(text: str) -> QualityViolation | None:
    """Check Flesch-Kincaid grade level — social media should be grade 8-12.

    FK Grade = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    Grade > 12 means prose is too academic/dense for social media audiences.
    Only fires when there are enough sentences (>=3) for the metric to be stable.
    """
    if not text:
        return None
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) < 3:
        return None
    words = text.split()
    if len(words) < 10:
        return None
    total_syllables = sum(_count_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = total_syllables / len(words)
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    if grade > FK_GRADE_THRESHOLD:
        return QualityViolation(
            check="flesch_kincaid_high",
            message=(
                f"Flesch-Kincaid grade {grade:.1f} — too academic for social media "
                f"(target ≤ {FK_GRADE_THRESHOLD:.0f}). Simplify vocabulary and shorten sentences."
            ),
            penalty=15,
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
            message=("No numbers and no proper nouns found — content is generic with no evidence"),
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
# Structural AI-detection checks
# ---------------------------------------------------------------------------

_SENTENCE_END_RE = re.compile(r"[.!?]+")


def _check_sentence_length_variance(text: str) -> QualityViolation | None:
    """Flag text where all sentences are suspiciously similar in length.

    Low variance in sentence word-counts is a strong AI-generation signal.
    Only fires when there are enough sentences (>=5) for the metric to be
    meaningful.
    """
    if not text:
        return None
    sentences = [s.strip() for s in _SENTENCE_END_RE.split(text) if s.strip()]
    if len(sentences) < 5:
        return None
    word_counts = [len(s.split()) for s in sentences]
    std_dev = statistics.pstdev(word_counts)
    if std_dev < 4:
        return QualityViolation(
            check="sentence_variance_low",
            message=(
                f"Sentence lengths too uniform (std dev {std_dev:.1f} words) "
                "— AI-typical pattern. Mix short and long sentences."
            ),
            penalty=15,
        )
    return None


def _check_single_sentence_paragraphs(text: str, platform: Platform) -> QualityViolation | None:
    """Check that LinkedIn posts have enough short, punchy paragraphs.

    Top LinkedIn creators use 30%+ single-sentence paragraphs for scanability.
    Only applies to LinkedIn and only when there are enough paragraphs (>=3)
    to make the metric meaningful.
    """
    if platform != Platform.LINKEDIN:
        return None
    # Split on blank lines or single newlines
    paragraphs = [p.strip() for p in re.split(r"\n\n|\n", text) if p.strip()]
    if len(paragraphs) < 3:
        return None
    single_sentence_count = 0
    for para in paragraphs:
        sentence_parts = [s.strip() for s in _SENTENCE_END_RE.split(para) if s.strip()]
        if len(sentence_parts) <= 1:
            single_sentence_count += 1
    ratio = single_sentence_count / len(paragraphs)
    if ratio < 0.30:
        return QualityViolation(
            check="few_short_paragraphs",
            message=(
                f"Only {ratio:.0%} single-sentence paragraphs — "
                "LinkedIn top creators use 30%+. Break up some paragraphs."
            ),
            penalty=10,
        )
    return None


def _check_opening_word_diversity(text: str) -> QualityViolation | None:
    """Flag when most paragraphs start with the same small set of words.

    If the 4 generic openers (I, The, In, It) account for >50% of paragraph
    openings, the text reads as AI-generated.  Only fires when there are
    enough paragraphs (>=4) for the metric to matter.
    """
    if not text:
        return None
    paragraphs = [p.strip() for p in re.split(r"\n\n|\n", text) if p.strip()]
    if len(paragraphs) < 4:
        return None
    generic_openers = {"i", "the", "in", "it"}
    first_words = []
    for para in paragraphs:
        words = para.split()
        if words:
            first_words.append(words[0].lower().rstrip(".,;:!?"))
    if not first_words:
        return None
    generic_count = sum(1 for w in first_words if w in generic_openers)
    ratio = generic_count / len(first_words)
    if ratio > 0.50:
        # List which generic openers were actually used
        used = sorted({w for w in first_words if w in generic_openers})
        return QualityViolation(
            check="repetitive_openers",
            message=(f"Opening words are repetitive ({', '.join(used)}). Vary paragraph starts."),
            penalty=10,
        )
    return None


def _check_linkedin_i_opening(text: str, platform: Platform) -> QualityViolation | None:
    """Flag LinkedIn posts that start with 'I' — algorithm penalizes it.

    Voice profile rule: "NEVER start with 'I'. LinkedIn algorithm penalizes it.
    Start with a number, observation, or bold claim."
    Only applies to LinkedIn platform.
    """
    if platform != Platform.LINKEDIN:
        return None
    stripped = text.lstrip()
    if not stripped:
        return None
    # Check if post starts with "I " or "I'" (e.g., "I've", "I'm")
    if stripped.startswith("I ") or stripped.startswith("I'"):
        return QualityViolation(
            check="linkedin_i_opening",
            message=(
                "LinkedIn post starts with 'I' — algorithm penalizes this. "
                "Open with a number, observation, or bold claim instead."
            ),
            penalty=15,
        )
    return None


def _check_consecutive_same_length(text: str) -> QualityViolation | None:
    """Flag 3+ consecutive sentences with nearly identical word counts.

    When consecutive sentences all land within +/-2 words of each other,
    the rhythm feels mechanical — a strong AI-generation signal.
    """
    if not text:
        return None
    sentences = [s.strip() for s in _SENTENCE_END_RE.split(text) if s.strip()]
    if len(sentences) < 3:
        return None
    word_counts = [len(s.split()) for s in sentences]
    streak = 1
    for i in range(1, len(word_counts)):
        if abs(word_counts[i] - word_counts[i - 1]) <= 2:
            streak += 1
            if streak >= 3:
                return QualityViolation(
                    check="mechanical_rhythm",
                    message=("3+ consecutive sentences with similar length — mechanical rhythm."),
                    penalty=10,
                )
        else:
            streak = 1
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

    # Flesch-Kincaid grade level (academic complexity)
    v = _check_flesch_kincaid(text)
    if v:
        violations.append(v)

    # Specificity (numbers, proper nouns)
    v = _check_specificity(text)
    if v:
        violations.append(v)

    # Structural AI-detection checks
    v = _check_sentence_length_variance(text)
    if v:
        violations.append(v)

    v = _check_single_sentence_paragraphs(text, piece.platform)
    if v:
        violations.append(v)

    v = _check_opening_word_diversity(text)
    if v:
        violations.append(v)

    v = _check_consecutive_same_length(text)
    if v:
        violations.append(v)

    # LinkedIn-specific: don't start with "I"
    v = _check_linkedin_i_opening(text, piece.platform)
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
