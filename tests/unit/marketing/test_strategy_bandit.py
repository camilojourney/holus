"""Tests for Thompson Sampling strategy bandit."""

from pathlib import Path

import pytest

from holus.agents.marketing.strategy_bandit import BanditArm, StrategyBandit


@pytest.fixture
def bandit(tmp_path):
    b = StrategyBandit(arms_path=tmp_path / "arms.json")
    b.register_arm("invoz", "carousel", "linkedin")
    b.register_arm("genpeli", "text_post", "linkedin")
    b.register_arm("invoz", "text_post", "twitter")
    return b


class TestBanditArm:
    def test_initial_state(self):
        arm = BanditArm(arm_id="test:arm:id", product="test", content_type="arm", platform="id")
        assert arm.n == 0
        assert arm.avg_reward is None
        assert not arm.is_activated

    def test_update_single(self):
        arm = BanditArm(arm_id="x:y:z", product="x", content_type="y", platform="z")
        arm.update(0.8)
        assert arm.n == 1
        assert arm.avg_reward == 0.8

    def test_update_multiple(self):
        arm = BanditArm(arm_id="x:y:z", product="x", content_type="y", platform="z")
        for r in [0.6, 0.8, 0.7]:
            arm.update(r)
        assert arm.n == 3
        assert abs(arm.avg_reward - 0.7) < 0.01

    def test_sample_theta_in_range(self):
        arm = BanditArm(arm_id="x:y:z", product="x", content_type="y", platform="z")
        for _ in range(10):
            arm.update(0.7)
        theta = arm.sample_theta()
        assert 0.0 <= theta <= 1.0

    def test_activated_after_threshold(self):
        arm = BanditArm(arm_id="x:y:z", product="x", content_type="y", platform="z")
        for _ in range(30):
            arm.update(0.75)
        assert arm.is_activated

    def test_serialization(self):
        arm = BanditArm(arm_id="a:b:c", product="a", content_type="b", platform="c")
        arm.update(0.9)
        d = arm.to_dict()
        arm2 = BanditArm.from_dict(d)
        assert arm2.n == 1
        assert arm2.arm_id == "a:b:c"


class TestStrategyBandit:
    def test_register_arm(self, bandit):
        arms = bandit.list_arms()
        assert len(arms) == 3

    def test_suggest_returns_result(self, bandit):
        result = bandit.suggest()
        assert result is not None
        assert result.arm.arm_id in ["invoz:carousel:linkedin", "genpeli:text_post:linkedin", "invoz:text_post:twitter"]
        assert result.is_exploration  # no data yet

    def test_suggest_with_platform_filter(self, bandit):
        result = bandit.suggest(platform="twitter")
        assert result is not None
        assert result.arm.platform == "twitter"

    def test_update_and_persist(self, bandit, tmp_path):
        bandit.update("invoz:carousel:linkedin", 0.85)
        # Reload from disk
        b2 = StrategyBandit(arms_path=tmp_path / "arms.json")
        arm = b2.get_arm("invoz:carousel:linkedin")
        assert arm is not None
        assert arm.n == 1
        assert arm.avg_reward == 0.85

    def test_suggest_prefers_high_reward(self, bandit):
        # Give one arm much higher rewards
        for _ in range(20):
            bandit.update("invoz:carousel:linkedin", 0.9)
            bandit.update("genpeli:text_post:linkedin", 0.3)

        # Over many samples, the high-reward arm should be picked more
        picks = {"invoz:carousel:linkedin": 0, "genpeli:text_post:linkedin": 0}
        for _ in range(100):
            result = bandit.suggest(platform="linkedin")
            if result and result.arm.arm_id in picks:
                picks[result.arm.arm_id] += 1

        assert picks["invoz:carousel:linkedin"] > picks["genpeli:text_post:linkedin"]

    def test_summary(self, bandit):
        bandit.update("invoz:carousel:linkedin", 0.8)
        s = bandit.summary()
        assert s["total_arms"] == 3
        assert s["total_observations"] == 1

    def test_backfill(self, bandit):
        entries = [
            {"task_type": "carousel", "judge_score": 0.8, "metadata": {"product": "invoz", "content_type": "carousel", "platform": "linkedin"}},
            {"task_type": "text_post", "judge_score": 0.6, "metadata": {"product": "genpeli", "content_type": "text_post", "platform": "linkedin"}},
        ]
        count = bandit.backfill_from_trajectory(entries)
        assert count == 2
        arm = bandit.get_arm("invoz:carousel:linkedin")
        assert arm.n == 1

    def test_empty_bandit_suggest_none(self, tmp_path):
        b = StrategyBandit(arms_path=tmp_path / "empty.json")
        assert b.suggest() is None
