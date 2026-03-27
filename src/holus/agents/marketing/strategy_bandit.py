"""Thompson Sampling strategy engine for content decisions.

Multi-armed bandit that decides WHAT content to create next based on
historical performance. Each (product x content_type x platform) combination
is an "arm." The algorithm balances exploitation (repeat what works) with
exploration (try new combos).

Uses Normal-Inverse-Gamma priors for continuous rewards (not Beta/Bernoulli).
Activated only when n >= 30 engagement-scored entries per arm exist.

Usage::

    bandit = StrategyBandit()
    arm = bandit.suggest()  # → {"product": "invoz", "content_type": "carousel", "platform": "linkedin"}
    # ... generate content, get reward ...
    bandit.update(arm_id="invoz:carousel:linkedin", reward=0.82)
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ARMS_PATH = Path(".self-improvement/bandit_arms.json")
MIN_OBSERVATIONS_TO_ACTIVATE = 30  # Per consultation: n >= 30 per arm


@dataclass
class BanditArm:
    """A single arm in the multi-armed bandit."""

    arm_id: str  # "product:content_type:platform"
    product: str
    content_type: str
    platform: str

    # Normal-Inverse-Gamma sufficient statistics
    n: int = 0  # observation count
    mean: float = 0.5  # running mean of rewards
    sum_sq: float = 0.0  # sum of squared deviations
    total_reward: float = 0.0

    # Prior parameters
    mu_0: float = 0.5  # prior mean
    kappa_0: float = 1.0  # prior precision
    alpha_0: float = 2.0  # prior shape
    beta_0: float = 0.5  # prior rate

    @property
    def is_activated(self) -> bool:
        """Arm has enough data for meaningful Thompson Sampling."""
        return self.n >= MIN_OBSERVATIONS_TO_ACTIVATE

    @property
    def avg_reward(self) -> float | None:
        """Average observed reward, or None if no observations."""
        return self.total_reward / self.n if self.n > 0 else None

    def sample_theta(self) -> float:
        """Sample from the posterior distribution (Normal-Inverse-Gamma).

        Returns a sampled expected reward for this arm.
        If not enough data, samples from the prior (wide, exploratory).
        """
        # Posterior parameters
        kappa_n = self.kappa_0 + self.n
        mu_n = (self.kappa_0 * self.mu_0 + self.n * self.mean) / kappa_n
        alpha_n = self.alpha_0 + self.n / 2
        beta_n = (
            self.beta_0
            + self.sum_sq / 2
            + (self.kappa_0 * self.n * (self.mean - self.mu_0) ** 2) / (2 * kappa_n)
        )

        # Sample variance from Inverse-Gamma
        # Use Gamma(alpha, 1/beta) then invert
        if alpha_n > 0 and beta_n > 0:
            precision = random.gammavariate(alpha_n, 1.0 / beta_n)
            variance = 1.0 / max(precision, 1e-10)
        else:
            variance = 0.25  # fallback

        # Sample mean from Normal(mu_n, variance / kappa_n)
        std = math.sqrt(max(variance / kappa_n, 1e-10))
        theta = random.gauss(mu_n, std)

        # Clamp to [0, 1] range
        return max(0.0, min(1.0, theta))

    def update(self, reward: float) -> None:
        """Update sufficient statistics with a new observation."""
        self.n += 1
        self.total_reward += reward
        old_mean = self.mean
        self.mean = self.total_reward / self.n
        # Welford's online algorithm for sum of squared deviations
        self.sum_sq += (reward - old_mean) * (reward - self.mean)

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "product": self.product,
            "content_type": self.content_type,
            "platform": self.platform,
            "n": self.n,
            "mean": round(self.mean, 4),
            "sum_sq": round(self.sum_sq, 6),
            "total_reward": round(self.total_reward, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BanditArm:
        return cls(
            arm_id=data["arm_id"],
            product=data["product"],
            content_type=data["content_type"],
            platform=data["platform"],
            n=data.get("n", 0),
            mean=data.get("mean", 0.5),
            sum_sq=data.get("sum_sq", 0.0),
            total_reward=data.get("total_reward", 0.0),
        )


@dataclass
class SuggestionResult:
    """Result of a Thompson Sampling suggestion."""

    arm: BanditArm
    sampled_theta: float
    is_exploration: bool  # True if arm has < MIN_OBSERVATIONS


class StrategyBandit:
    """Thompson Sampling multi-armed bandit for content strategy.

    Manages arms, persists state to JSON, and provides suggest/update API.
    """

    def __init__(self, arms_path: Path | str = DEFAULT_ARMS_PATH) -> None:
        self._arms_path = Path(arms_path)
        self._arms: dict[str, BanditArm] = {}
        self._load()

    def _load(self) -> None:
        """Load arm state from JSON file."""
        if not self._arms_path.exists():
            return
        try:
            data = json.loads(self._arms_path.read_text(encoding="utf-8"))
            for arm_data in data.get("arms", []):
                arm = BanditArm.from_dict(arm_data)
                self._arms[arm.arm_id] = arm
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load bandit arms: %s", exc)

    def _save(self) -> None:
        """Persist arm state to JSON file."""
        self._arms_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "arms": [arm.to_dict() for arm in self._arms.values()],
            "total_observations": sum(a.n for a in self._arms.values()),
        }
        self._arms_path.write_text(json.dumps(data, indent=2))

    def register_arm(
        self,
        product: str,
        content_type: str,
        platform: str,
    ) -> BanditArm:
        """Register a new arm or return existing one."""
        arm_id = f"{product}:{content_type}:{platform}"
        if arm_id not in self._arms:
            self._arms[arm_id] = BanditArm(
                arm_id=arm_id,
                product=product,
                content_type=content_type,
                platform=platform,
            )
            self._save()
        return self._arms[arm_id]

    def suggest(
        self,
        *,
        platform: str | None = None,
        max_arms: int = 5,
    ) -> SuggestionResult | None:
        """Suggest which content to create next via Thompson Sampling.

        Optionally filter to a specific platform. Caps active arms at max_arms
        (per consultation: prevent 20-arm convergence problem).

        Returns None if no arms are registered.
        """
        candidates = list(self._arms.values())
        if platform:
            candidates = [a for a in candidates if a.platform == platform]

        if not candidates:
            return None

        # Cap at max_arms highest-performing + some exploratory
        if len(candidates) > max_arms:
            # Sort by avg reward (None = unexplored = high priority)
            candidates.sort(
                key=lambda a: a.avg_reward if a.avg_reward is not None else 1.0,
                reverse=True,
            )
            # Keep top performers + at least 1 unexplored
            unexplored = [a for a in candidates if a.n < MIN_OBSERVATIONS_TO_ACTIVATE]
            explored = [a for a in candidates if a.n >= MIN_OBSERVATIONS_TO_ACTIVATE]
            candidates = (
                explored[: max_arms - 1] + unexplored[:1] if unexplored else explored[:max_arms]
            )

        # Thompson Sampling: sample theta from each arm's posterior
        best_arm = None
        best_theta = -1.0
        for arm in candidates:
            theta = arm.sample_theta()
            if theta > best_theta:
                best_theta = theta
                best_arm = arm

        if best_arm is None:
            return None

        return SuggestionResult(
            arm=best_arm,
            sampled_theta=best_theta,
            is_exploration=not best_arm.is_activated,
        )

    def update(self, arm_id: str, reward: float) -> None:
        """Update an arm with an observed reward."""
        if arm_id not in self._arms:
            logger.warning("Unknown arm: %s", arm_id)
            return

        self._arms[arm_id].update(reward)
        self._save()

    def get_arm(self, arm_id: str) -> BanditArm | None:
        """Get an arm by ID."""
        return self._arms.get(arm_id)

    def list_arms(self, *, platform: str | None = None) -> list[BanditArm]:
        """List all arms, optionally filtered by platform."""
        arms = list(self._arms.values())
        if platform:
            arms = [a for a in arms if a.platform == platform]
        return sorted(arms, key=lambda a: a.avg_reward or 0, reverse=True)

    def summary(self) -> dict[str, Any]:
        """Return summary statistics for all arms."""
        arms = list(self._arms.values())
        activated = [a for a in arms if a.is_activated]
        return {
            "total_arms": len(arms),
            "activated_arms": len(activated),
            "total_observations": sum(a.n for a in arms),
            "top_arm": max(arms, key=lambda a: a.avg_reward or 0).arm_id if arms else None,
            "top_reward": max((a.avg_reward or 0) for a in arms) if arms else None,
        }

    def backfill_from_trajectory(self, trajectory_entries: list[dict[str, Any]]) -> int:
        """Seed arm statistics from existing trajectory data.

        Returns number of entries processed.
        """
        count = 0
        for entry in trajectory_entries:
            meta = entry.get("metadata", {})
            product = meta.get("product", "unknown")
            content_type = meta.get("content_type", entry.get("task_type", "unknown"))
            platform = meta.get("platform", "unknown")
            reward = meta.get("blended_reward") or entry.get("judge_score")

            if reward is None or platform == "unknown":
                continue

            arm = self.register_arm(product, content_type, platform)
            arm.update(float(reward))
            count += 1

        self._save()
        return count
