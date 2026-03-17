"""Tests for advanced self-improvement analytics."""

from holus.self_improvement.analytics import ab_test_significance, classify_failures, detect_anomalies


class TestABTestSignificance:
    def test_insufficient_samples(self):
        result = ab_test_significance([0.8, 0.7], [0.9])
        assert not result["significant"]
        assert result["recommendation"] == "CONTINUE_TEST"

    def test_significant_improvement(self):
        control = [0.5, 0.55, 0.48, 0.52, 0.51, 0.49, 0.53, 0.50, 0.47, 0.52]
        challenger = [0.8, 0.82, 0.79, 0.81, 0.78, 0.83, 0.80, 0.77, 0.82, 0.81]
        result = ab_test_significance(control, challenger)
        assert result["significant"]
        assert result["lift"] > 0.3
        assert result["recommendation"] == "PROMOTE_CHALLENGER"

    def test_no_significant_difference(self):
        control = [0.7, 0.72, 0.68, 0.71, 0.69, 0.73, 0.70, 0.72, 0.68, 0.71]
        challenger = [0.71, 0.70, 0.72, 0.69, 0.73, 0.70, 0.71, 0.72, 0.68, 0.70]
        result = ab_test_significance(control, challenger)
        assert result["recommendation"] == "CONTINUE_TEST"

    def test_significant_regression(self):
        control = [0.8, 0.82, 0.79, 0.81, 0.78, 0.83, 0.80, 0.77, 0.82, 0.81]
        challenger = [0.5, 0.48, 0.52, 0.49, 0.51, 0.47, 0.50, 0.53, 0.48, 0.52]
        result = ab_test_significance(control, challenger)
        assert result["significant"]
        assert result["lift"] < -0.2
        assert result["recommendation"] == "ROLLBACK_CHALLENGER"

    def test_returns_p_value(self):
        control = [0.6] * 20
        challenger = [0.9] * 20
        result = ab_test_significance(control, challenger)
        assert "p_value" in result
        assert result["p_value"] < 0.05


class TestClassifyFailures:
    # These depend on trajectory file — tested via integration
    pass


class TestAnomalyDetection:
    # These depend on trajectory file — tested via integration
    pass
