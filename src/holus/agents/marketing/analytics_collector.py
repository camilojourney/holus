"""Analytics collector — fetches post-publish engagement data into trajectory.

Reads published content from the queue, fetches engagement metrics from Holus
Social API, computes the engagement reward signal, and writes the result back
to trajectory.jsonl.

This closes the feedback loop: generate → judge → publish → collect → learn.

Usage::

    from holus.agents.marketing.analytics_collector import collect_analytics
    results = await collect_analytics()

Designed to run as a daily cron job (24h after each publish batch).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

QUEUE_DIR = Path("data/content-queue")

# Platform-specific reward weights (from engineering consultation)
REWARD_WEIGHTS: dict[str, dict[str, float]] = {
    "linkedin": {"comments": 0.4, "shares": 0.3, "likes": 0.2, "saves": 0.1},
    "instagram": {"saves": 0.4, "shares": 0.3, "comments": 0.2, "likes": 0.1},
    "tiktok": {"watch_time": 0.5, "shares": 0.3, "comments": 0.2},
    "twitter": {"retweets": 0.4, "quotes": 0.3, "replies": 0.2, "likes": 0.1},
    "twitter_x": {"retweets": 0.4, "quotes": 0.3, "replies": 0.2, "likes": 0.1},
    "threads": {"reposts": 0.3, "quotes": 0.3, "likes": 0.2, "shares": 0.2},
    "facebook": {"shares": 0.4, "comments": 0.3, "likes": 0.2, "clicks": 0.1},
}


def compute_engagement_signal(analytics: dict[str, Any], platform: str) -> float:
    """Compute normalized engagement signal from platform-specific metrics.

    Returns a value between 0.0 and 1.0.
    """
    weights = REWARD_WEIGHTS.get(platform.lower(), REWARD_WEIGHTS["linkedin"])
    views = max(analytics.get("views", 0) or analytics.get("impressions", 0) or 1, 1)

    score = 0.0
    for metric, weight in weights.items():
        value = analytics.get(metric, 0) or 0
        score += weight * (value / views)

    # Normalize — engagement rates above 10% are exceptional
    return min(score * 10, 1.0)


def compute_blended_reward(
    judge_score: float | None,
    engagement_signal: float,
    *,
    n_paired_observations: int = 0,
) -> float:
    """Compute blended reward with dynamic weighting.

    - Before 100 paired observations: judge-only (engagement data too sparse)
    - After 100 paired observations: 0.3 * judge + 0.7 * engagement
    """
    if judge_score is None:
        return engagement_signal

    if n_paired_observations < 100:
        # Phase 1: judge-dominant (engagement data is sparse)
        alpha = max(0.3, 1.0 - n_paired_observations / 100)
        return alpha * judge_score + (1 - alpha) * engagement_signal

    # Phase 2: engagement-dominant (real data available)
    return 0.3 * judge_score + 0.7 * engagement_signal


def _load_published_pieces(max_age_days: int = 8) -> list[dict[str, Any]]:
    """Load published queue items that need analytics collection."""
    if not QUEUE_DIR.exists():
        return []

    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
    items: list[dict[str, Any]] = []

    for pattern in ("*.yaml", "*.json"):
        for path in sorted(QUEUE_DIR.glob(pattern)):
            try:
                text = path.read_text(encoding="utf-8")
                data = yaml.safe_load(text) if path.suffix == ".yaml" else json.loads(text)

                if not isinstance(data, dict):
                    continue
                if data.get("status") != "published":
                    continue
                if not data.get("post_id"):
                    continue

                # Skip if already has engagement data
                if data.get("engagement_collected"):
                    continue

                # Skip if published too long ago
                published_at = data.get("published_at", "")
                if published_at and published_at < cutoff:
                    continue

                data["_file_path"] = str(path)
                items.append(data)
            except Exception:
                continue

    return items


def _count_paired_observations() -> int:
    """Count trajectory entries that have both judge_score and engagement data."""
    traj_path = Path(".self-improvement/memory/trajectory.jsonl")
    if not traj_path.exists():
        return 0

    count = 0
    with open(traj_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line.strip())
                if (
                    entry.get("judge_score") is not None
                    and entry.get("metadata", {}).get("engagement_signal") is not None
                ):
                    count += 1
            except (json.JSONDecodeError, AttributeError):
                continue
    return count


async def collect_analytics(*, max_age_days: int = 8) -> list[dict[str, Any]]:
    """Fetch engagement data for published content and update trajectory.

    Returns list of {piece_id, platform, engagement_signal, blended_reward}.
    """
    from holus.integrations.holus_social_api import HolusSocialAPIClient
    from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

    pieces = _load_published_pieces(max_age_days=max_age_days)
    if not pieces:
        logger.info("No published pieces need analytics collection")
        return []

    n_paired = _count_paired_observations()
    tl = TrajectoryLogger(Path(".self-improvement/memory/trajectory.jsonl"))
    results: list[dict[str, Any]] = []

    import os

    api_key = os.environ.get("HOLUS_SOCIAL_API_KEY") or os.environ.get("POSTING_API_KEY", "")
    if not api_key:
        logger.error("HOLUS_SOCIAL_API_KEY not set — cannot collect analytics")
        return []

    async with HolusSocialAPIClient(api_key=api_key) as client:
        for piece in pieces:
            post_id = piece["post_id"]
            platform = piece.get("platform", "linkedin")
            piece_id = piece.get("piece_id", Path(piece["_file_path"]).stem)
            judge_score = piece.get("judge_score")

            try:
                analytics = await client.get_post_analytics(post_id)
            except Exception as exc:
                logger.warning("Analytics fetch failed for %s: %s", post_id, exc)
                continue

            engagement = compute_engagement_signal(analytics, platform)
            reward = compute_blended_reward(judge_score, engagement, n_paired_observations=n_paired)

            # Log to trajectory
            tl.append(
                TrajectoryEntry(
                    agent_id="analytics-collector",
                    task_type="engagement_collection",
                    task_summary=f"Analytics for {piece_id} on {platform}",
                    status="success",
                    judge_score=judge_score,
                    metadata={
                        "schema_version": 2,
                        "piece_id": piece_id,
                        "post_id": post_id,
                        "platform": platform,
                        "analytics_raw": {
                            k: v
                            for k, v in analytics.items()
                            if isinstance(v, (int, float, str)) and k != "raw_response"
                        },
                        "engagement_signal": round(engagement, 4),
                        "blended_reward": round(reward, 4),
                        "n_paired_observations": n_paired,
                        "reward_alpha": max(0.3, 1.0 - n_paired / 100) if n_paired < 100 else 0.3,
                    },
                )
            )

            # Mark piece as analytics-collected
            file_path = piece["_file_path"]
            path = Path(file_path)
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) if path.suffix == ".yaml" else json.loads(text)
            data["engagement_collected"] = True
            data["engagement_signal"] = round(engagement, 4)
            data["blended_reward"] = round(reward, 4)
            data["analytics_collected_at"] = datetime.now(UTC).isoformat()
            if path.suffix == ".yaml":
                path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
            else:
                path.write_text(json.dumps(data, indent=2))

            results.append(
                {
                    "piece_id": piece_id,
                    "post_id": post_id,
                    "platform": platform,
                    "product": piece.get("product", "unknown"),
                    "content_type": piece.get("content_type", "unknown"),
                    "arm_id": piece.get("arm_id"),
                    "engagement_signal": round(engagement, 4),
                    "blended_reward": round(reward, 4),
                    "views": analytics.get("views", 0),
                    "likes": analytics.get("likes", 0),
                    "comments": analytics.get("comments", 0),
                    "shares": analytics.get("shares", 0),
                }
            )

            n_paired += 1  # Increment for next calculation

    logger.info("Collected analytics for %d pieces", len(results))
    return results
