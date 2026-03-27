"""Tests for gap detection and failure classification."""

from holus.self_improvement.gap_detector import classify_failure, detect_gaps


class TestClassifyFailure:
    def test_capability_gap_no_tool(self):
        result = classify_failure("Create video", "", "no tool available for video rendering")
        assert result == "capability_gap"

    def test_capability_gap_not_implemented(self):
        result = classify_failure("Post to TikTok", "", "TikTok integration not implemented")
        assert result == "capability_gap"

    def test_data_gap(self):
        result = classify_failure("Write Spanish post", "", "no data on Spanish voice profile")
        assert result == "data_gap"

    def test_prompt_issue(self):
        result = classify_failure("Write carousel", "", "off-topic, didn't follow the brief")
        assert result == "prompt_issue"

    def test_quality_issue_default(self):
        result = classify_failure("Write post", "mediocre output", "hook is weak, lacks authority")
        assert result == "quality_issue"

    def test_empty_feedback(self):
        result = classify_failure("task", "output", "")
        assert result == "quality_issue"


class TestDetectGaps:
    def _make_entries(self, n: int, platform: str, content_type: str, failure_class: str):
        return [
            {
                "status": "failure",
                "judge_score": 0.3,
                "judge_feedback": f"Failed: {failure_class}",
                "task_type": content_type,
                "timestamp": f"2026-03-{10 + i}T00:00:00Z",
                "metadata": {
                    "platform": platform,
                    "content_type": content_type,
                    "failure_class": failure_class,
                },
            }
            for i in range(n)
        ]

    def test_detects_capability_gap(self):
        entries = self._make_entries(5, "tiktok", "video_reel", "capability_gap")
        gaps = detect_gaps(entries, min_failures=3)
        assert len(gaps) == 1
        assert gaps[0]["type"] == "capability_gap"
        assert gaps[0]["platform"] == "tiktok"
        assert gaps[0]["evidence_count"] == 5

    def test_below_threshold_not_detected(self):
        entries = self._make_entries(2, "tiktok", "video_reel", "capability_gap")
        gaps = detect_gaps(entries, min_failures=3)
        assert len(gaps) == 0

    def test_multiple_gap_types(self):
        entries = self._make_entries(
            4, "tiktok", "video_reel", "capability_gap"
        ) + self._make_entries(3, "instagram", "story", "data_gap")
        gaps = detect_gaps(entries, min_failures=3)
        assert len(gaps) == 2

    def test_quality_issues_from_low_scores(self):
        entries = [
            {
                "status": "success",
                "judge_score": 0.3,
                "judge_feedback": "weak hook",
                "task_type": "text_post",
                "timestamp": f"2026-03-{10 + i}T00:00:00Z",
                "metadata": {
                    "platform": "linkedin",
                    "content_type": "text_post",
                    "failure_class": "quality_issue",
                },
            }
            for i in range(4)
        ]
        gaps = detect_gaps(entries, min_failures=3)
        assert len(gaps) == 1
        assert gaps[0]["type"] == "quality_issue"
