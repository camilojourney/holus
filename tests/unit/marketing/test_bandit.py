"""Tests for ε-greedy multi-armed bandit (SPEC-035)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from holus.agents.marketing.bandit import Bandit, DEFAULT_ARMS


@pytest.fixture
def tmp_bandit(tmp_path: Path) -> Bandit:
    """Bandit with temp state file."""
    return Bandit(state_path=tmp_path / "bandit-state.json")


def test_bandit_initializes_with_default_arms(tmp_bandit: Bandit) -> None:
    stats = tmp_bandit.arm_stats()
    assert set(stats.keys()) == set(DEFAULT_ARMS)
    for arm in DEFAULT_ARMS:
        assert stats[arm]["trials"] == 0
        assert stats[arm]["wins"] == 0


def test_select_arms_returns_n_distinct(tmp_bandit: Bandit) -> None:
    arms = tmp_bandit.select_arms(n=2)
    assert len(arms) == 2
    assert len(set(arms)) == 2  # distinct


def test_select_arms_pure_exploration_when_no_trials(tmp_bandit: Bandit) -> None:
    """With 0 trials, epsilon=1.0 — pure random."""
    # Run many times to confirm randomness (not always same arm)
    selections: set[str] = set()
    for _ in range(20):
        arms = tmp_bandit.select_arms(n=1)
        selections.update(arms)
    # Should have selected more than 1 unique arm across 20 runs
    assert len(selections) > 1


def test_update_increments_trials(tmp_bandit: Bandit) -> None:
    arm = DEFAULT_ARMS[0]
    tmp_bandit.update(arm, won=True)
    tmp_bandit.update(arm, won=False)
    stats = tmp_bandit.arm_stats()
    assert stats[arm]["trials"] == 2
    assert stats[arm]["wins"] == 1


def test_update_persists_to_file(tmp_path: Path) -> None:
    path = tmp_path / "bandit-state.json"
    bandit = Bandit(state_path=path)
    bandit.update(DEFAULT_ARMS[0], won=True)

    # Reload from disk
    bandit2 = Bandit(state_path=path)
    stats = bandit2.arm_stats()
    assert stats[DEFAULT_ARMS[0]]["trials"] == 1
    assert stats[DEFAULT_ARMS[0]]["wins"] == 1


def test_epsilon_phases(tmp_path: Path) -> None:
    path = tmp_path / "bandit-state.json"
    bandit = Bandit(state_path=path)

    assert bandit._epsilon() == 1.0  # 0 trials

    # Simulate 10 trials
    for _ in range(10):
        bandit.update(DEFAULT_ARMS[0], won=True)
    assert bandit._epsilon() == 0.3  # phase 2

    # Simulate 30+ trials
    for _ in range(25):
        bandit.update(DEFAULT_ARMS[0], won=True)
    assert bandit._epsilon() == 0.1  # phase 3


def test_select_arms_respects_n_limit(tmp_bandit: Bandit) -> None:
    arms = tmp_bandit.select_arms(n=3)
    assert len(arms) <= 3
    assert len(set(arms)) == len(arms)  # distinct


def test_win_rate_calculation(tmp_bandit: Bandit) -> None:
    arm = DEFAULT_ARMS[0]
    tmp_bandit.update(arm, won=True)
    tmp_bandit.update(arm, won=True)
    tmp_bandit.update(arm, won=False)
    stats = tmp_bandit.arm_stats()
    assert stats[arm]["win_rate"] == pytest.approx(2 / 3, abs=0.001)
