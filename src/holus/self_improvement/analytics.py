"""Advanced analytics for the self-improvement loop.

Failure taxonomy, cost-effectiveness tracking, anomaly detection,
and A/B test statistical significance.

Usage::

    from holus.self_improvement.analytics import (
        classify_failures, cost_effectiveness, detect_anomalies, ab_test_significance
    )
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")


def _read_trajectory(days: int = 30) -> list[dict[str, Any]]:
    if not TRAJECTORY_PATH.exists():
        return []
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    entries = []
    with open(TRAJECTORY_PATH, encoding="utf-8") as fh:
        for line in fh:
            try:
                e = json.loads(line.strip())
                if e.get("timestamp", "") >= cutoff:
                    entries.append(e)
            except (json.JSONDecodeError, AttributeError):
                continue
    return entries


# ---------------------------------------------------------------------------
# 6.3: Failure taxonomy
# ---------------------------------------------------------------------------


def classify_failures(days: int = 30) -> dict[str, Any]:
    """Classify all failures into a taxonomy for targeted fixes.

    Categories:
    - hook_weak: judge feedback mentions hook/opening
    - voice_off: judge feedback mentions voice/tone/formal
    - too_long: judge feedback mentions length/brevity
    - off_topic: judge feedback mentions topic/relevance
    - no_cta: judge feedback mentions CTA/call to action
    - capability_gap: metadata has failure_class=capability_gap
    - other: everything else
    """
    entries = _read_trajectory(days)
    failures = [
        e for e in entries
        if (e.get("judge_score") is not None and e["judge_score"] < 0.5)
        or e.get("status") in ("failure", "error")
    ]

    taxonomy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    keyword_map = {
        "hook_weak": ["hook", "opening", "first line", "scroll", "attention"],
        "voice_off": ["voice", "tone", "formal", "hedging", "we ", "corporate"],
        "too_long": ["long", "verbose", "brevity", "wordy", "trim", "cut"],
        "off_topic": ["topic", "relevance", "off-topic", "unrelated", "thesis"],
        "no_cta": ["cta", "call to action", "closing", "question"],
    }

    for entry in failures:
        feedback = (entry.get("judge_feedback") or "").lower()
        meta = entry.get("metadata", {})

        if meta.get("failure_class") == "capability_gap":
            taxonomy["capability_gap"].append(entry)
            continue

        classified = False
        for category, keywords in keyword_map.items():
            if any(kw in feedback for kw in keywords):
                taxonomy[category].append(entry)
                classified = True
                break

        if not classified:
            taxonomy["other"].append(entry)

    return {
        "total_failures": len(failures),
        "categories": {
            cat: {"count": len(items), "pct": round(len(items) / max(len(failures), 1) * 100, 1)}
            for cat, items in sorted(taxonomy.items(), key=lambda x: len(x[1]), reverse=True)
        },
        "top_category": max(taxonomy, key=lambda k: len(taxonomy[k])) if taxonomy else None,
    }


# ---------------------------------------------------------------------------
# 6.4: Cost-effectiveness ratio
# ---------------------------------------------------------------------------


def cost_effectiveness(days: int = 30) -> dict[str, Any]:
    """Calculate engagement per dollar spent, by content type.

    Returns: {content_type: {total_cost, total_engagement, cost_per_engagement, n}}
    """
    entries = _read_trajectory(days)

    by_type: dict[str, dict[str, float]] = defaultdict(
        lambda: {"total_cost": 0.0, "total_engagement": 0.0, "n": 0}
    )

    for entry in entries:
        meta = entry.get("metadata", {})
        content_type = meta.get("content_type", entry.get("task_type", "unknown"))
        cost = entry.get("cost_usd", 0.0)
        engagement = meta.get("engagement_signal", 0.0)

        if cost > 0 or engagement > 0:
            by_type[content_type]["total_cost"] += cost
            by_type[content_type]["total_engagement"] += engagement
            by_type[content_type]["n"] += 1

    result = {}
    for ct, data in by_type.items():
        cost_per = data["total_cost"] / max(data["total_engagement"], 0.001)
        result[ct] = {
            "total_cost_usd": round(data["total_cost"], 4),
            "total_engagement": round(data["total_engagement"], 4),
            "cost_per_engagement": round(cost_per, 4),
            "n": int(data["n"]),
        }

    return {"by_content_type": result, "days": days}


# ---------------------------------------------------------------------------
# 6.5: Anomaly detection
# ---------------------------------------------------------------------------


def detect_anomalies(days: int = 30, z_threshold: float = 2.0) -> list[dict[str, Any]]:
    """Detect anomalous score drops week-over-week.

    Compares this week's average score to the prior 3 weeks.
    Flags if the drop exceeds z_threshold standard deviations.
    """
    entries = _read_trajectory(days)

    # Group scores by week
    weekly_scores: dict[str, list[float]] = defaultdict(list)
    for entry in entries:
        score = entry.get("judge_score")
        if score is None:
            continue
        ts = entry.get("timestamp", "")[:10]
        if not ts:
            continue
        # Get ISO week number
        try:
            dt = datetime.fromisoformat(ts)
            week_key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            weekly_scores[week_key].append(score)
        except (ValueError, TypeError):
            continue

    if len(weekly_scores) < 2:
        return []

    weeks = sorted(weekly_scores.keys())
    anomalies: list[dict[str, Any]] = []

    for i in range(1, len(weeks)):
        current_week = weeks[i]
        current_scores = weekly_scores[current_week]
        current_avg = sum(current_scores) / len(current_scores)

        # Compare to prior weeks
        prior_scores = []
        for j in range(max(0, i - 3), i):
            prior_scores.extend(weekly_scores[weeks[j]])

        if len(prior_scores) < 3:
            continue

        prior_avg = sum(prior_scores) / len(prior_scores)
        prior_std = (sum((s - prior_avg) ** 2 for s in prior_scores) / len(prior_scores)) ** 0.5

        if prior_std == 0:
            continue

        z_score = (prior_avg - current_avg) / prior_std  # Positive = drop

        if z_score >= z_threshold:
            anomalies.append({
                "week": current_week,
                "avg_score": round(current_avg, 3),
                "prior_avg": round(prior_avg, 3),
                "z_score": round(z_score, 2),
                "n_current": len(current_scores),
                "n_prior": len(prior_scores),
                "severity": "HIGH" if z_score >= 3.0 else "MEDIUM",
            })

    return anomalies


# ---------------------------------------------------------------------------
# 6.6: A/B test statistical significance
# ---------------------------------------------------------------------------


def ab_test_significance(
    control_scores: list[float],
    challenger_scores: list[float],
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Calculate statistical significance of an A/B test.

    Uses Welch's t-test (unequal variances, unequal sample sizes).
    Returns p-value, confidence interval, and recommendation.
    """
    n_a = len(control_scores)
    n_b = len(challenger_scores)

    if n_a < 5 or n_b < 5:
        return {
            "significant": False,
            "reason": f"Insufficient samples (control={n_a}, challenger={n_b}, need 5 each)",
            "recommendation": "CONTINUE_TEST",
        }

    mean_a = sum(control_scores) / n_a
    mean_b = sum(challenger_scores) / n_b
    var_a = sum((x - mean_a) ** 2 for x in control_scores) / (n_a - 1)
    var_b = sum((x - mean_b) ** 2 for x in challenger_scores) / (n_b - 1)

    # Welch's t-test
    se = math.sqrt(var_a / n_a + var_b / n_b) if (var_a / n_a + var_b / n_b) > 0 else 0.001
    t_stat = (mean_b - mean_a) / se

    # Approximate degrees of freedom (Welch-Satterthwaite)
    num = (var_a / n_a + var_b / n_b) ** 2
    denom = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    df = num / denom if denom > 0 else min(n_a, n_b) - 1

    # Approximate p-value using normal distribution (good for df > 30)
    # For smaller df, this overestimates significance slightly
    z = abs(t_stat)
    # Standard normal CDF approximation (Abramowitz & Stegun)
    p = 1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))
    p_two_tailed = 2 * p

    alpha = 1 - confidence
    significant = p_two_tailed < alpha
    lift = (mean_b - mean_a) / mean_a if mean_a > 0 else 0

    if significant and lift > 0.05:
        recommendation = "PROMOTE_CHALLENGER"
    elif significant and lift < -0.05:
        recommendation = "ROLLBACK_CHALLENGER"
    else:
        recommendation = "CONTINUE_TEST"

    return {
        "significant": significant,
        "p_value": round(p_two_tailed, 4),
        "t_statistic": round(t_stat, 3),
        "degrees_of_freedom": round(df, 1),
        "control_mean": round(mean_a, 4),
        "challenger_mean": round(mean_b, 4),
        "lift": round(lift, 4),
        "n_control": n_a,
        "n_challenger": n_b,
        "recommendation": recommendation,
    }
