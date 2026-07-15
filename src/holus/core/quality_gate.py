"""Deterministic content quality gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

DEFAULT_PASS_THRESHOLD = 7.0


@dataclass(frozen=True)
class QualityGateResult:
    """Result of applying a quality gate to generated content pieces."""

    accepted_pieces: list[dict[str, Any]] = field(default_factory=list)
    discarded_pieces: list[dict[str, Any]] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    pass_count: int = 0
    hard_fail_count: int = 0


def enforce_quality_gate(
    pieces: Sequence[dict[str, Any]],
    *,
    scorer: Callable[[dict[str, Any]], float],
    threshold: float = DEFAULT_PASS_THRESHOLD,
) -> QualityGateResult:
    """Accept pieces scoring at or above threshold and discard the rest."""
    accepted: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []
    scores: list[float] = []

    for piece in pieces:
        score = float(scorer(piece))
        scores.append(score)
        if score >= threshold:
            accepted.append(piece)
        else:
            discarded.append(piece)

    return QualityGateResult(
        accepted_pieces=accepted,
        discarded_pieces=discarded,
        scores=scores,
        pass_count=len(accepted),
        hard_fail_count=len(discarded),
    )
