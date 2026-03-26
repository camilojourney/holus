"""48h performance loop — reads engagement data, updates bandit weights.

Called by a scheduler 48h after each post goes live.
Reads analytics from social-media-mcp, computes win signal,
updates bandit arm weights, logs to trajectory.jsonl.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from holus.agents.marketing.bandit import Bandit

logger = logging.getLogger(__name__)

_TRAJECTORY_PATH = Path(__file__).parents[4] / ".self-improvement" / "memory" / "trajectory.jsonl"


class PerformanceLoop:
    """48h post-publish engagement reader and bandit updater."""

    def __init__(
        self,
        bandit: Bandit | None = None,
        trajectory_path: Path | None = None,
    ) -> None:
        self._bandit = bandit or Bandit()
        self._trajectory_path = trajectory_path or _TRAJECTORY_PATH

    def process(
        self,
        post_id: str,
        arm_id: str,
        engagement_data: dict[str, Any],
        baseline_rate: float | None = None,
    ) -> dict[str, Any]:
        """Process 48h engagement data for a post.

        Args:
            post_id: The post identifier
            arm_id: Which visual treatment arm was used
            engagement_data: Dict with keys: impressions, reactions, comments, shares
            baseline_rate: Median engagement rate for the week (for win signal)
                           If None, uses 3% as default threshold

        Returns:
            Dict with win signal, updated arm stats, and log entry
        """
        impressions = engagement_data.get("impressions", 0)
        reactions = engagement_data.get("reactions", 0)
        comments = engagement_data.get("comments", 0)
        shares = engagement_data.get("shares", 0)

        # Engagement rate = (reactions + comments + shares) / impressions
        engagement_rate = 0.0
        if impressions > 0:
            engagement_rate = (reactions + comments + shares) / impressions

        # Win signal: beat baseline (default 3%)
        threshold = baseline_rate if baseline_rate is not None else 0.03
        won = engagement_rate > threshold

        # Update bandit
        self._bandit.update(arm_id, won)
        arm_stats = self._bandit.arm_stats().get(arm_id, {})

        result: dict[str, Any] = {
            "post_id": post_id,
            "arm_id": arm_id,
            "engagement_rate": round(engagement_rate, 4),
            "threshold": threshold,
            "won": won,
            "arm_stats": arm_stats,
        }

        # Log to trajectory
        self._log(post_id, arm_id, engagement_rate, won, engagement_data)

        logger.info(
            "performance_loop: post=%s arm=%s rate=%.3f won=%s",
            post_id, arm_id, engagement_rate, won,
        )
        return result

    def _log(
        self,
        post_id: str,
        arm_id: str,
        engagement_rate: float,
        won: bool,
        raw: dict[str, Any],
    ) -> None:
        entry = {
            "agent_id": "performance-loop",
            "timestamp": datetime.now(UTC).isoformat(),
            "task_type": "performance_readback",
            "post_id": post_id,
            "arm_id": arm_id,
            "engagement_rate": engagement_rate,
            "won": won,
            "raw_engagement": raw,
            "status": "success",
        }
        self._trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._trajectory_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
