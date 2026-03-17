"""Judge calibration — detect and correct divergence between judge and humans.

When a human rejects content that the judge PASSED, this is a calibration
signal. Accumulated signals indicate the judge rubric needs updating.

Two mechanisms:
1. Calibration alerts: flag when judge-human agreement drops
2. Preference learning: build a preference model from approve/reject data

Usage::

    calibrator = JudgeCalibrator()
    report = calibrator.analyze()
    # report.agreement_rate, report.false_positive_rate, report.recommendations
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")


@dataclass
class CalibrationReport:
    """Results of judge calibration analysis."""

    total_judged: int
    total_human_reviewed: int
    agreement_rate: float  # % of time judge and human agree
    false_positive_rate: float  # Judge PASS but human REJECT
    false_negative_rate: float  # Judge FAIL but human would PASS (estimated)
    calibration_needed: bool
    problem_dimensions: list[str]  # Which rubric dimensions are miscalibrated
    recommendations: list[str]


class JudgeCalibrator:
    """Analyze judge-human agreement and detect miscalibration."""

    def __init__(self, trajectory_path: Path = TRAJECTORY_PATH) -> None:
        self._path = trajectory_path

    def analyze(self, days: int = 90) -> CalibrationReport:
        """Analyze judge-human agreement over the last N days."""
        if not self._path.exists():
            return CalibrationReport(
                total_judged=0, total_human_reviewed=0, agreement_rate=1.0,
                false_positive_rate=0.0, false_negative_rate=0.0,
                calibration_needed=False, problem_dimensions=[], recommendations=[],
            )

        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        entries = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line.strip())
                    if e.get("timestamp", "") >= cutoff:
                        entries.append(e)
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Find human rejection entries
        human_rejections = [
            e for e in entries
            if e.get("metadata", {}).get("rejected_by") == "human"
        ]

        # Find all judged entries
        judged = [e for e in entries if e.get("judge_score") is not None]

        # Find false positives: judge PASS (>= 0.8) but human rejected
        false_positives = [
            e for e in human_rejections
            if e.get("metadata", {}).get("judge_calibration_needed")
        ]

        total_judged = len(judged)
        total_reviewed = len(human_rejections)
        fp_count = len(false_positives)

        # Agreement rate: human-reviewed pieces where judge and human agree
        # (This underestimates because we only see rejections, not approvals)
        agreement_rate = 1.0 - (fp_count / max(total_reviewed, 1))
        fp_rate = fp_count / max(total_judged, 1)

        # Analyze which dimensions are miscalibrated
        problem_dims = self._find_problem_dimensions(false_positives)

        # Generate recommendations
        recommendations = []
        if fp_rate > 0.15:
            recommendations.append(
                f"CRITICAL: {fp_rate:.0%} false positive rate. Judge passes content humans reject. "
                "Tighten rubric thresholds or add missing evaluation dimensions."
            )
        if problem_dims:
            recommendations.append(
                f"Rubric dimensions to review: {', '.join(problem_dims)}. "
                "These dimensions show consistent judge-human disagreement."
            )
        if total_reviewed > 10 and agreement_rate < 0.7:
            recommendations.append(
                "Consider epochal judge recalibration: run old+new judge on 50 pieces, "
                "compute mapping function, then switch."
            )

        return CalibrationReport(
            total_judged=total_judged,
            total_human_reviewed=total_reviewed,
            agreement_rate=round(agreement_rate, 3),
            false_positive_rate=round(fp_rate, 3),
            false_negative_rate=0.0,  # Can't measure without human PASS data
            calibration_needed=fp_rate > 0.1 or agreement_rate < 0.8,
            problem_dimensions=problem_dims,
            recommendations=recommendations,
        )

    def _find_problem_dimensions(
        self,
        false_positives: list[dict[str, Any]],
    ) -> list[str]:
        """Identify which judge dimensions consistently miscalibrate."""
        # Extract rejection reasons and find common themes
        reasons = [
            e.get("metadata", {}).get("rejection_reason", "")
            for e in false_positives
        ]

        dimension_mentions: dict[str, int] = defaultdict(int)
        dimension_keywords = {
            "hook_strength": ["hook", "opening", "first line", "scroll stopper"],
            "voice_fidelity": ["voice", "tone", "formal", "corporate", "hedging"],
            "narrative_arc": ["story", "narrative", "flow", "structure"],
            "readability": ["long", "verbose", "complex", "confusing"],
            "authority_signal": ["authority", "credibility", "proof", "evidence"],
            "engagement_potential": ["boring", "engagement", "comments", "interaction"],
        }

        for reason in reasons:
            reason_lower = reason.lower()
            for dim, keywords in dimension_keywords.items():
                if any(kw in reason_lower for kw in keywords):
                    dimension_mentions[dim] += 1

        # Return dimensions mentioned in > 30% of false positives
        threshold = max(len(false_positives) * 0.3, 1)
        return [dim for dim, count in dimension_mentions.items() if count >= threshold]

    def build_preference_pairs(self, days: int = 90) -> list[dict[str, Any]]:
        """Build preference pairs from human approve/reject decisions.

        Each pair: {chosen: approved_text, rejected: rejected_text, context: ...}
        These pairs can be used for RLHF-style preference learning or
        to fine-tune the judge.
        """
        if not self._path.exists():
            return []

        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        entries = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line.strip())
                    if e.get("timestamp", "") >= cutoff:
                        entries.append(e)
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Group by similar tasks
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in entries:
            meta = e.get("metadata", {})
            key = f"{meta.get('content_type', 'unknown')}:{meta.get('platform', 'unknown')}"
            by_type[key].append(e)

        pairs: list[dict[str, Any]] = []
        for key, group in by_type.items():
            approved = [e for e in group if e.get("status") == "success" and e.get("judge_score", 0) >= 0.8]
            rejected = [e for e in group if e.get("metadata", {}).get("rejected_by") == "human"]

            for rej in rejected:
                for app in approved[:3]:  # Max 3 pairs per rejection
                    pairs.append({
                        "chosen": app.get("task_summary", ""),
                        "rejected": rej.get("task_summary", ""),
                        "context": key,
                        "chosen_score": app.get("judge_score"),
                        "rejected_score": rej.get("judge_score"),
                    })

        return pairs
