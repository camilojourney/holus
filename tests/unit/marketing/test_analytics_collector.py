"""Tests for analytics collector reward computation."""

from holus.agents.marketing.analytics_collector import (
    compute_blended_reward,
    compute_engagement_signal,
)


class TestEngagementSignal:
    def test_linkedin_comments_weighted_highest(self):
        analytics = {"views": 1000, "comments": 50, "shares": 10, "likes": 100, "saves": 5}
        signal = compute_engagement_signal(analytics, "linkedin")
        assert signal > 0
        # Comments at 0.4 weight should dominate
        assert signal < 1.0

    def test_instagram_saves_weighted_highest(self):
        analytics = {"views": 1000, "saves": 100, "shares": 10, "comments": 5, "likes": 50}
        signal = compute_engagement_signal(analytics, "instagram")
        assert signal > 0

    def test_zero_views_no_division_error(self):
        analytics = {"views": 0, "comments": 5}
        signal = compute_engagement_signal(analytics, "linkedin")
        assert signal >= 0

    def test_empty_analytics(self):
        signal = compute_engagement_signal({}, "linkedin")
        assert signal == 0.0

    def test_capped_at_one(self):
        # Extreme engagement should cap at 1.0
        analytics = {"views": 10, "comments": 100, "shares": 100, "likes": 100, "saves": 100}
        signal = compute_engagement_signal(analytics, "linkedin")
        assert signal == 1.0

    def test_unknown_platform_uses_linkedin_default(self):
        analytics = {"views": 1000, "comments": 10}
        signal = compute_engagement_signal(analytics, "unknown_platform")
        assert signal > 0

    def test_twitter_uses_retweets(self):
        analytics = {"views": 1000, "retweets": 50, "quotes": 10, "replies": 20, "likes": 100}
        signal = compute_engagement_signal(analytics, "twitter")
        assert signal > 0


class TestBlendedReward:
    def test_judge_only_when_no_engagement(self):
        reward = compute_blended_reward(0.85, 0.0, n_paired_observations=0)
        # With 0 observations, alpha=1.0 → reward = judge_score
        assert reward == 0.85

    def test_engagement_dominates_after_100(self):
        reward = compute_blended_reward(0.5, 0.9, n_paired_observations=200)
        # 0.3 * 0.5 + 0.7 * 0.9 = 0.15 + 0.63 = 0.78
        assert abs(reward - 0.78) < 0.01

    def test_gradual_transition(self):
        # At 50 observations, alpha = max(0.3, 1.0 - 50/100) = 0.5
        reward = compute_blended_reward(0.8, 0.6, n_paired_observations=50)
        expected = 0.5 * 0.8 + 0.5 * 0.6  # = 0.7
        assert abs(reward - expected) < 0.01

    def test_none_judge_returns_engagement_only(self):
        reward = compute_blended_reward(None, 0.75)
        assert reward == 0.75

    def test_alpha_never_below_0_3(self):
        reward_90 = compute_blended_reward(1.0, 0.0, n_paired_observations=90)
        # alpha = max(0.3, 1.0 - 0.9) = 0.3
        assert abs(reward_90 - 0.3) < 0.01
