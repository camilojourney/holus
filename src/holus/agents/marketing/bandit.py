"""ε-greedy multi-armed bandit for visual treatment diversity.

State persisted in data/bandit-state.json.
Arms = visual treatment combinations (background + typography + layout).

Phase 1 (< 10 trials): ε=1.0 (pure exploration)
Phase 2 (10-30 trials): ε=0.3
Phase 3 (30+ trials):   ε=0.1
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# Default treatment combinations — each arm is a visual style
DEFAULT_ARMS: list[str] = [
    "dark_gradient__large_headline__centered",
    "light_clean__body_heavy__split",
    "bold_color__minimal__asymmetric",
    "dark_gradient__body_heavy__split",
    "light_clean__large_headline__centered",
    "bold_color__large_headline__asymmetric",
]

_DEFAULT_STATE_PATH = Path(__file__).parents[4] / "data" / "bandit-state.json"


class Bandit:
    """ε-greedy multi-armed bandit for visual treatment selection."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._path = state_path or _DEFAULT_STATE_PATH
        self._state = self._load()

    # -- State I/O ---------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        # Bootstrap with default arms
        return {
            "arms": {
                arm: {"wins": 0, "trials": 0}
                for arm in DEFAULT_ARMS
            },
            "total_trials": 0,
        }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._state, indent=2))

    # -- Core API ----------------------------------------------------------

    def _epsilon(self) -> float:
        total = self._state.get("total_trials", 0)
        if total < 10:
            return 1.0   # pure exploration
        if total < 30:
            return 0.3
        return 0.1

    def select_arms(self, n: int = 2) -> list[str]:
        """Select n arms for variant generation.

        Uses ε-greedy: with probability ε pick randomly (explore),
        otherwise pick the arm with the highest win rate (exploit).
        Returns n distinct arm ids.
        """
        arms = list(self._state["arms"].keys())
        if len(arms) < n:
            return arms

        eps = self._epsilon()
        chosen: list[str] = []

        # Always include at least 1 exploit arm if not pure exploration
        if eps < 1.0:
            best = max(
                arms,
                key=lambda a: (
                    self._state["arms"][a]["wins"] / max(self._state["arms"][a]["trials"], 1)
                ),
            )
            chosen.append(best)

        # Fill remaining slots with explore or exploit
        remaining = [a for a in arms if a not in chosen]
        while len(chosen) < n and remaining:
            if random.random() < eps:
                # explore
                arm = random.choice(remaining)
            else:
                # exploit best of remaining
                arm = max(
                    remaining,
                    key=lambda a: (
                        self._state["arms"][a]["wins"] / max(self._state["arms"][a]["trials"], 1)
                    ),
                )
            chosen.append(arm)
            remaining.remove(arm)

        return chosen

    def update(self, arm_id: str, won: bool) -> None:
        """Record outcome for an arm. won=True if engagement > median."""
        if arm_id not in self._state["arms"]:
            self._state["arms"][arm_id] = {"wins": 0, "trials": 0}
        self._state["arms"][arm_id]["trials"] += 1
        if won:
            self._state["arms"][arm_id]["wins"] += 1
        self._state["total_trials"] = self._state.get("total_trials", 0) + 1
        self._save()

    def arm_stats(self) -> dict[str, dict[str, Any]]:
        """Return win rate stats for all arms."""
        stats: dict[str, dict[str, Any]] = {}
        for arm_id, counts in self._state["arms"].items():
            trials = counts["trials"]
            wins = counts["wins"]
            stats[arm_id] = {
                "trials": trials,
                "wins": wins,
                "win_rate": round(wins / trials, 3) if trials > 0 else 0.0,
            }
        return stats
