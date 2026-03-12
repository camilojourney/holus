"""Quality gate enforcement for Holus content pieces.

Every content piece produced in the CREATING phase is scored before posting.
Three possible outcomes:

- **Hard fail** (score < 4): discard immediately, log ``quality_hard_fail``.
- **Soft fail** (score 4-6): regenerate once with reviewer feedback, re-score.
  - Still < 6 after regen → discard, log ``quality_soft_fail``.
  - >= 6 after regen → accept.
- **Pass** (score >= 7): accept, log ``quality_pass``.

Usage::

    result = enforce_quality_gate(pieces, scorer=my_scorer)
    context.quality_scores = result.quality_scores
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Score thresholds
_HARD_FAIL_MAX = 4.0   # score < 4 → hard fail (exclusive upper bound)
_SOFT_FAIL_MAX = 7.0   # score 4-6 (< 7) -> soft fail; try regen
_REGEN_MIN = 6.0       # after regen, >= 6 → accept


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class QualityResult(BaseModel):
    """Result of running the quality gate over a batch of content pieces.

    Attributes:
        accepted_pieces: Content pieces that passed the quality gate.
        discarded_pieces: Content pieces that were discarded (hard or soft fail).
        quality_scores: Final score for every input piece (accepted and discarded),
            in the same order as the input list. Scores are in [0.0, 10.0].
        hard_fail_count: Number of pieces that failed with score < 4.
        soft_fail_count: Number of pieces that failed after regeneration.
        pass_count: Number of pieces that passed outright (score >= 7).
        regen_accepted_count: Number of pieces accepted after regeneration.
    """

    accepted_pieces: list[Any] = Field(default_factory=list)
    discarded_pieces: list[Any] = Field(default_factory=list)
    quality_scores: list[float] = Field(default_factory=list)
    hard_fail_count: int = 0
    soft_fail_count: int = 0
    pass_count: int = 0
    regen_accepted_count: int = 0


# ---------------------------------------------------------------------------
# Regeneration callback type
# ---------------------------------------------------------------------------

# A scorer takes a content piece and returns a float score in [0.0, 10.0].
ScorerFn = Callable[[Any], float]

# A regenerator takes a content piece + reviewer feedback string and returns
# a new (improved) content piece. Optional — if not provided, soft-fail pieces
# are discarded without regen.
RegeneratorFn = Callable[[Any, str], Any]

# A reviewer takes a content piece and returns a feedback string explaining
# what is wrong. Optional — a default message is used if not provided.
ReviewerFn = Callable[[Any], str]


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def enforce_quality_gate(
    content_pieces: list[Any],
    scorer: ScorerFn,
    *,
    regenerator: RegeneratorFn | None = None,
    reviewer: ReviewerFn | None = None,
) -> QualityResult:
    """Enforce the quality gate over a list of content pieces.

    Each piece is scored (1-10). Based on the score:

    - score < 4  → hard fail: discard, log ``quality_hard_fail``.
    - 4 <= score < 7 → soft fail: regenerate once (if ``regenerator`` provided).
      - Re-score regenerated piece.
      - score >= 6 → accept regenerated piece.
      - score < 6  → discard, log ``quality_soft_fail``.
    - score >= 7 → pass: accept, log ``quality_pass``.

    Args:
        content_pieces: List of content items to evaluate.
        scorer: Callable ``(piece) -> float`` returning a score in [0.0, 10.0].
        regenerator: Optional callable ``(piece, feedback) -> new_piece`` used
            during soft-fail recovery. If omitted, soft-fail pieces are discarded.
        reviewer: Optional callable ``(piece) -> str`` returning reviewer feedback
            used as the prompt for regeneration. Defaults to a generic message.

    Returns:
        :class:`QualityResult` with accepted/discarded lists, scores, and counts.
    """
    result = QualityResult()

    for piece in content_pieces:
        score = float(scorer(piece))
        final_score = score

        if score < _HARD_FAIL_MAX:
            # Hard fail: score < 4
            logger.info(
                "quality_hard_fail",
                score=score,
                piece_repr=repr(piece)[:80],
            )
            result.discarded_pieces.append(piece)
            result.hard_fail_count += 1

        elif score < _SOFT_FAIL_MAX:
            # Soft fail: 4 <= score < 7
            if regenerator is not None:
                feedback = reviewer(piece) if reviewer is not None else _default_feedback(score)
                regenerated = regenerator(piece, feedback)
                regen_score = float(scorer(regenerated))
                final_score = regen_score

                if regen_score >= _REGEN_MIN:
                    # Accepted after regen
                    logger.info(
                        "quality_regen_accepted",
                        original_score=score,
                        regen_score=regen_score,
                    )
                    result.accepted_pieces.append(regenerated)
                    result.regen_accepted_count += 1
                else:
                    # Still below threshold — discard
                    logger.info(
                        "quality_soft_fail",
                        original_score=score,
                        regen_score=regen_score,
                    )
                    result.discarded_pieces.append(piece)
                    result.soft_fail_count += 1
            else:
                # No regenerator — discard soft fail
                logger.info(
                    "quality_soft_fail",
                    score=score,
                    reason="no regenerator provided",
                )
                result.discarded_pieces.append(piece)
                result.soft_fail_count += 1

        else:
            # Pass: score >= 7
            logger.info(
                "quality_pass",
                score=score,
                piece_repr=repr(piece)[:80],
            )
            result.accepted_pieces.append(piece)
            result.pass_count += 1

        result.quality_scores.append(final_score)

    logger.info(
        "quality_gate_complete",
        total=len(content_pieces),
        accepted=len(result.accepted_pieces),
        discarded=len(result.discarded_pieces),
        hard_fails=result.hard_fail_count,
        soft_fails=result.soft_fail_count,
        passes=result.pass_count,
        regen_accepted=result.regen_accepted_count,
    )

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_feedback(score: float) -> str:
    """Generate a generic reviewer feedback message based on score."""
    return (
        f"Content scored {score:.1f}/10 which is below the quality threshold. "
        "Please improve clarity, relevance, and engagement before resubmitting."
    )
