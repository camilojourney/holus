"""Tests for JudgeAgent retry logic and response parsing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from holus.self_improvement.judge import JudgeAgent, JudgeVerdict

DEFAULT_JUDGE_MODEL = "anthropic/claude-sonnet-4-6"
OVERRIDE_JUDGE_MODEL = "anthropic/claude-opus-4-6"


def _valid_judge_response(verdict: str = "PASS", score: float = 0.85) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "score": score,
            "dimension_scores": {"correctness": 0.9, "completeness": 0.8},
            "feedback": "Good output.",
            "pass_threshold_met": score >= 0.8,
        }
    )


class TestParseResponse:
    def test_valid_pass(self):
        result = JudgeAgent._parse_response(_valid_judge_response("PASS", 0.9))
        assert result.verdict == JudgeVerdict.PASS
        assert result.score == 0.9
        assert result.pass_threshold_met is True

    def test_valid_partial(self):
        result = JudgeAgent._parse_response(_valid_judge_response("PARTIAL", 0.6))
        assert result.verdict == JudgeVerdict.PARTIAL
        assert result.score == 0.6

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            JudgeAgent._parse_response("not json at all")

    def test_unknown_verdict_defaults_to_fail(self):
        resp = json.dumps({"verdict": "MAYBE", "score": 0.5, "feedback": "Unclear"})
        result = JudgeAgent._parse_response(resp)
        assert result.verdict == JudgeVerdict.FAIL


class TestRetryLogic:
    def test_success_on_first_attempt(self):
        judge = JudgeAgent()
        with patch.object(judge, "_call_llm", return_value=_valid_judge_response()):
            result = judge.evaluate(task="test", task_type="default", output="output")
        assert result.verdict == JudgeVerdict.PASS
        assert result.score == 0.85

    def test_retry_on_invalid_json_then_succeed(self):
        judge = JudgeAgent()
        call_count = 0

        def _mock_call(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "invalid json {{{"
            return _valid_judge_response()

        with patch.object(judge, "_call_llm", side_effect=_mock_call):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                retry_delay=0.01,  # Fast for tests
            )

        assert result.verdict == JudgeVerdict.PASS
        assert call_count == 2

    def test_retry_on_timeout_then_succeed(self):
        judge = JudgeAgent()
        call_count = 0

        def _mock_call(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("connection timed out")
            return _valid_judge_response()

        with patch.object(judge, "_call_llm", side_effect=_mock_call):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                retry_delay=0.01,
            )

        assert result.verdict == JudgeVerdict.PASS
        assert call_count == 2

    def test_retry_on_connection_error_then_succeed(self):
        judge = JudgeAgent()
        call_count = 0

        def _mock_call(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("HTTP 503: Service Unavailable")
            return _valid_judge_response()

        with patch.object(judge, "_call_llm", side_effect=_mock_call):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                retry_delay=0.01,
            )

        assert result.verdict == JudgeVerdict.PASS
        assert call_count == 2

    def test_all_retries_exhausted_returns_fail(self):
        judge = JudgeAgent()
        with patch.object(judge, "_call_llm", side_effect=TimeoutError("timeout")):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                max_retries=2,
                retry_delay=0.01,
            )

        assert result.verdict == JudgeVerdict.FAIL
        assert result.score == 0.0
        assert "2 attempts" in result.feedback

    def test_non_transient_error_no_retry(self):
        judge = JudgeAgent()
        call_count = 0

        def _mock_call(msg):
            nonlocal call_count
            call_count += 1
            raise ValueError("bad argument")

        with patch.object(judge, "_call_llm", side_effect=_mock_call):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                retry_delay=0.01,
            )

        assert result.verdict == JudgeVerdict.FAIL
        assert call_count == 1  # No retry for non-transient
        assert "bad argument" in result.feedback

    def test_custom_max_retries(self):
        judge = JudgeAgent()
        call_count = 0

        def _mock_call(msg):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return "bad json"
            return _valid_judge_response()

        with patch.object(judge, "_call_llm", side_effect=_mock_call):
            result = judge.evaluate(
                task="test",
                task_type="default",
                output="output",
                max_retries=3,
                retry_delay=0.01,
            )

        assert result.verdict == JudgeVerdict.PASS
        assert call_count == 3


class TestCallLlm:
    def test_http_5xx_raises_connection_error(self):
        judge = JudgeAgent()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"

        with (
            patch("requests.post", return_value=mock_resp),
            pytest.raises(ConnectionError, match="503"),
        ):
            judge._call_llm("test message")

    def test_http_4xx_raises_http_error(self):
        judge = JudgeAgent()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch("requests.post", return_value=mock_resp), pytest.raises(Exception, match="401"):
            judge._call_llm("test message")

    def test_payload_uses_default_model_without_network(self):
        judge = JudgeAgent(proxy_url="http://test.invalid")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "{}"}}]}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            judge._call_llm("test message")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == DEFAULT_JUDGE_MODEL


class TestDefaultModel:
    def test_instance_uses_default_model_without_request(self):
        with patch("requests.post") as post:
            judge = JudgeAgent(proxy_url="http://test.invalid")
        assert judge._model == DEFAULT_JUDGE_MODEL
        post.assert_not_called()

    def test_explicit_model_override(self):
        override = OVERRIDE_JUDGE_MODEL
        with patch("requests.post") as post:
            judge = JudgeAgent(model=override, proxy_url="http://test.invalid")
        assert judge._model == override
        assert judge._model != DEFAULT_JUDGE_MODEL
        post.assert_not_called()
