"""Tests for holus.core.quality_gate — quality gate enforcement."""

from __future__ import annotations

from typing import Any

from holus.core.quality_gate import QualityResult, enforce_quality_gate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fixed_scorer(score: float):
    """Return a scorer that always returns *score*."""

    def scorer(_piece: Any) -> float:
        return score

    return scorer


def _sequence_scorer(scores: list[float]):
    """Return a scorer that returns scores in sequence (one per call)."""
    it = iter(scores)

    def scorer(_piece: Any) -> float:
        return next(it)

    return scorer


def _noop_regenerator(piece: Any, _feedback: str) -> Any:
    """Regenerator that returns the piece unchanged."""
    return piece


def _prefix_regenerator(prefix: str):
    """Regenerator that prefixes a string piece."""

    def regen(piece: Any, _feedback: str) -> Any:
        return f"{prefix}{piece}"

    return regen


# ---------------------------------------------------------------------------
# Hard fail (score < 4)
# ---------------------------------------------------------------------------


class TestHardFail:
    def test_single_hard_fail_piece_discarded(self) -> None:
        result = enforce_quality_gate(["bad content"], scorer=_fixed_scorer(2.0))

        assert result.discarded_pieces == ["bad content"]
        assert result.accepted_pieces == []
        assert result.hard_fail_count == 1
        assert result.quality_scores == [2.0]

    def test_score_zero_is_hard_fail(self) -> None:
        result = enforce_quality_gate(["zero"], scorer=_fixed_scorer(0.0))

        assert result.hard_fail_count == 1
        assert len(result.discarded_pieces) == 1

    def test_score_exactly_3_99_is_hard_fail(self) -> None:
        result = enforce_quality_gate(["borderline"], scorer=_fixed_scorer(3.99))

        assert result.hard_fail_count == 1

    def test_multiple_hard_fails(self) -> None:
        pieces = ["a", "b", "c"]
        result = enforce_quality_gate(pieces, scorer=_fixed_scorer(1.0))

        assert result.hard_fail_count == 3
        assert result.accepted_pieces == []
        assert len(result.discarded_pieces) == 3

    def test_hard_fail_score_recorded_in_quality_scores(self) -> None:
        result = enforce_quality_gate(["x"], scorer=_fixed_scorer(3.5))

        assert result.quality_scores == [3.5]

    def test_hard_fail_does_not_call_regenerator(self) -> None:
        calls: list[Any] = []

        def tracking_regen(piece: Any, feedback: str) -> Any:
            calls.append(piece)
            return piece

        enforce_quality_gate(["bad"], scorer=_fixed_scorer(1.0), regenerator=tracking_regen)

        assert calls == [], "Regenerator must not be called on hard fail"


# ---------------------------------------------------------------------------
# Soft fail (4 <= score < 7)
# ---------------------------------------------------------------------------


class TestSoftFail:
    def test_soft_fail_without_regenerator_discards(self) -> None:
        result = enforce_quality_gate(["mediocre"], scorer=_fixed_scorer(5.0))

        assert result.discarded_pieces == ["mediocre"]
        assert result.soft_fail_count == 1
        assert result.accepted_pieces == []

    def test_score_exactly_4_is_soft_fail(self) -> None:
        result = enforce_quality_gate(["x"], scorer=_fixed_scorer(4.0))

        assert result.soft_fail_count == 1

    def test_score_6_99_is_soft_fail(self) -> None:
        result = enforce_quality_gate(["x"], scorer=_fixed_scorer(6.99))

        assert result.soft_fail_count == 1

    def test_soft_fail_with_regen_accepted_when_regen_score_ge_6(self) -> None:
        # First call: original score = 5.0 (soft fail)
        # Second call: regen score = 6.5 (accepted)
        scorer = _sequence_scorer([5.0, 6.5])
        result = enforce_quality_gate(["mediocre"], scorer=scorer, regenerator=_noop_regenerator)

        assert result.accepted_pieces == ["mediocre"]
        assert result.regen_accepted_count == 1
        assert result.soft_fail_count == 0
        assert result.discarded_pieces == []

    def test_soft_fail_with_regen_discarded_when_regen_score_lt_6(self) -> None:
        # First call: 5.0 → soft fail; second: 4.5 → still below 6 → discard
        scorer = _sequence_scorer([5.0, 4.5])
        result = enforce_quality_gate(["mediocre"], scorer=scorer, regenerator=_noop_regenerator)

        assert result.discarded_pieces == ["mediocre"]
        assert result.soft_fail_count == 1
        assert result.regen_accepted_count == 0

    def test_soft_fail_regen_score_exactly_6_is_accepted(self) -> None:
        scorer = _sequence_scorer([5.0, 6.0])
        result = enforce_quality_gate(["piece"], scorer=scorer, regenerator=_noop_regenerator)

        assert result.regen_accepted_count == 1
        assert len(result.accepted_pieces) == 1

    def test_regen_score_is_recorded_not_original(self) -> None:
        scorer = _sequence_scorer([5.0, 6.5])
        result = enforce_quality_gate(["piece"], scorer=scorer, regenerator=_noop_regenerator)

        # quality_scores should contain the regen score (6.5), not the original (5.0)
        assert result.quality_scores == [6.5]

    def test_regenerator_receives_reviewer_feedback(self) -> None:
        feedback_received: list[str] = []

        def tracking_regen(piece: Any, feedback: str) -> Any:
            feedback_received.append(feedback)
            return piece

        scorer = _sequence_scorer([5.0, 6.0])
        enforce_quality_gate(["piece"], scorer=scorer, regenerator=tracking_regen)

        assert len(feedback_received) == 1
        assert len(feedback_received[0]) > 0

    def test_custom_reviewer_feedback_used(self) -> None:
        feedback_received: list[str] = []

        def tracking_regen(piece: Any, feedback: str) -> Any:
            feedback_received.append(feedback)
            return piece

        def custom_reviewer(_piece: Any) -> str:
            return "Custom feedback message"

        scorer = _sequence_scorer([5.0, 6.0])
        enforce_quality_gate(
            ["piece"],
            scorer=scorer,
            regenerator=tracking_regen,
            reviewer=custom_reviewer,
        )

        assert feedback_received == ["Custom feedback message"]

    def test_regenerated_piece_accepted_not_original(self) -> None:
        def regen(piece: Any, _feedback: str) -> Any:
            return f"improved:{piece}"

        scorer = _sequence_scorer([5.0, 7.0])
        result = enforce_quality_gate(["original"], scorer=scorer, regenerator=regen)

        assert result.accepted_pieces == ["improved:original"]


# ---------------------------------------------------------------------------
# Pass (score >= 7)
# ---------------------------------------------------------------------------


class TestPass:
    def test_single_pass(self) -> None:
        result = enforce_quality_gate(["great content"], scorer=_fixed_scorer(8.0))

        assert result.accepted_pieces == ["great content"]
        assert result.pass_count == 1
        assert result.discarded_pieces == []
        assert result.quality_scores == [8.0]

    def test_score_exactly_7_is_pass(self) -> None:
        result = enforce_quality_gate(["x"], scorer=_fixed_scorer(7.0))

        assert result.pass_count == 1

    def test_score_10_is_pass(self) -> None:
        result = enforce_quality_gate(["perfect"], scorer=_fixed_scorer(10.0))

        assert result.pass_count == 1

    def test_pass_does_not_call_regenerator(self) -> None:
        calls: list[Any] = []

        def tracking_regen(piece: Any, feedback: str) -> Any:
            calls.append(piece)
            return piece

        enforce_quality_gate(["great"], scorer=_fixed_scorer(9.0), regenerator=tracking_regen)

        assert calls == [], "Regenerator must not be called on pass"


# ---------------------------------------------------------------------------
# Mixed batch
# ---------------------------------------------------------------------------


class TestMixedBatch:
    def test_mixed_outcomes(self) -> None:
        # Scores: 2 (hard fail), 5 (soft fail, no regen), 8 (pass)
        pieces = ["bad", "mediocre", "great"]
        scores = [2.0, 5.0, 8.0]
        scorer = _sequence_scorer(scores)

        result = enforce_quality_gate(pieces, scorer=scorer)

        assert result.hard_fail_count == 1
        assert result.soft_fail_count == 1
        assert result.pass_count == 1
        assert result.accepted_pieces == ["great"]
        assert "bad" in result.discarded_pieces
        assert "mediocre" in result.discarded_pieces

    def test_quality_scores_preserve_order(self) -> None:
        pieces = ["a", "b", "c"]
        scores = [2.0, 6.5, 8.0]
        scorer = _sequence_scorer(scores)

        result = enforce_quality_gate(pieces, scorer=scorer)

        assert result.quality_scores == [2.0, 6.5, 8.0]

    def test_empty_list_returns_empty_result(self) -> None:
        result = enforce_quality_gate([], scorer=_fixed_scorer(5.0))

        assert result.accepted_pieces == []
        assert result.discarded_pieces == []
        assert result.quality_scores == []
        assert result.hard_fail_count == 0
        assert result.soft_fail_count == 0
        assert result.pass_count == 0

    def test_all_pass(self) -> None:
        pieces = ["a", "b", "c"]
        result = enforce_quality_gate(pieces, scorer=_fixed_scorer(9.0))

        assert result.pass_count == 3
        assert len(result.accepted_pieces) == 3
        assert result.hard_fail_count == 0

    def test_all_hard_fail(self) -> None:
        pieces = ["a", "b", "c"]
        result = enforce_quality_gate(pieces, scorer=_fixed_scorer(1.0))

        assert result.hard_fail_count == 3
        assert result.accepted_pieces == []


# ---------------------------------------------------------------------------
# QualityResult type
# ---------------------------------------------------------------------------


class TestQualityResultModel:
    def test_is_pydantic_model(self) -> None:
        result = QualityResult()
        assert isinstance(result, QualityResult)

    def test_default_values(self) -> None:
        result = QualityResult()
        assert result.accepted_pieces == []
        assert result.discarded_pieces == []
        assert result.quality_scores == []
        assert result.hard_fail_count == 0
        assert result.soft_fail_count == 0
        assert result.pass_count == 0
        assert result.regen_accepted_count == 0

    def test_can_set_fields(self) -> None:
        result = QualityResult(
            accepted_pieces=["a"],
            discarded_pieces=["b"],
            quality_scores=[8.0, 2.0],
            hard_fail_count=1,
            pass_count=1,
        )
        assert result.pass_count == 1
        assert result.hard_fail_count == 1


# ---------------------------------------------------------------------------
# Integration with CycleContext
# ---------------------------------------------------------------------------


class TestQualityGateCycleContextIntegration:
    """Verify quality_scores from QualityResult can be assigned to CycleContext."""

    def test_quality_scores_assignable_to_context(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from holus.core.cycle_state import CycleContext

        ctx = CycleContext.new(trajectory_path=tmp_path / "traj.jsonl")

        pieces = ["great", "mediocre", "bad"]
        scorer = _sequence_scorer([9.0, 5.0, 2.0])
        gate_result = enforce_quality_gate(pieces, scorer=scorer)

        ctx.quality_scores = gate_result.quality_scores

        assert ctx.quality_scores == [9.0, 5.0, 2.0]
        assert len(ctx.quality_scores) == 3
