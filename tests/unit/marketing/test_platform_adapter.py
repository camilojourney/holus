"""Tests for platform adapter and engagement normalization."""

from holus.agents.marketing.platform_adapter import normalize_engagement


class TestNormalizeEngagement:
    def test_raw_engagement_rate(self):
        analytics = {"engagement_rate": 5.0}
        result = normalize_engagement(analytics, "linkedin")
        assert 0 <= result <= 1.0

    def test_zero_engagement(self):
        result = normalize_engagement({}, "linkedin")
        assert result == 0.0

    def test_high_engagement_capped(self):
        analytics = {"engagement_rate": 50.0}
        result = normalize_engagement(analytics, "linkedin")
        assert result == 1.0

    def test_z_score_with_baseline(self):
        baseline = {"linkedin": {"mean": 3.0, "std": 1.5}}
        analytics = {"engagement_rate": 6.0}  # 2 std above mean
        result = normalize_engagement(analytics, "linkedin", baseline_stats=baseline)
        assert result > 0.8  # sigmoid(2) ≈ 0.88

    def test_z_score_below_mean(self):
        baseline = {"linkedin": {"mean": 3.0, "std": 1.5}}
        analytics = {"engagement_rate": 0.0}  # 2 std below mean
        result = normalize_engagement(analytics, "linkedin", baseline_stats=baseline)
        assert result < 0.2  # sigmoid(-2) ≈ 0.12

    def test_unknown_platform_uses_fallback(self):
        baseline = {"linkedin": {"mean": 3.0, "std": 1.5}}
        analytics = {"engagement_rate": 5.0}
        result = normalize_engagement(analytics, "tiktok", baseline_stats=baseline)
        assert result == 0.5  # No baseline for tiktok → raw / 10
