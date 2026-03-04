"""Tests for holus.self_improvement.judge."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from holus.self_improvement.judge import (
    JUDGE_SYSTEM_PROMPT,
    TASK_TYPE_RUBRICS,
    JudgeAgent,
    JudgeEvaluation,
    JudgeVerdict,
)

# ---------------------------------------------------------------------------
# JudgeVerdict enum
# ---------------------------------------------------------------------------


class TestJudgeVerdict:
    """Test the JudgeVerdict StrEnum."""

    def test_values(self) -> None:
        assert JudgeVerdict.PASS == "PASS"
        assert JudgeVerdict.FAIL == "FAIL"
        assert JudgeVerdict.PARTIAL == "PARTIAL"

    def test_members_count(self) -> None:
        assert len(JudgeVerdict) == 3

    def test_is_str(self) -> None:
        assert isinstance(JudgeVerdict.PASS, str)


# ---------------------------------------------------------------------------
# JudgeEvaluation dataclass
# ---------------------------------------------------------------------------


class TestJudgeEvaluation:
    """Test the JudgeEvaluation dataclass."""

    def test_create(self) -> None:
        ev = JudgeEvaluation(
            verdict=JudgeVerdict.PASS,
            score=0.9,
            dimension_scores={"correctness": 0.95, "completeness": 0.85},
            feedback="Good output",
            pass_threshold_met=True,
        )
        assert ev.verdict == JudgeVerdict.PASS
        assert ev.score == 0.9
        assert ev.pass_threshold_met is True

    def test_to_dict(self) -> None:
        ev = JudgeEvaluation(
            verdict=JudgeVerdict.PARTIAL,
            score=0.6,
            dimension_scores={"correctness": 0.7, "completeness": 0.5},
            feedback="Missing details",
            pass_threshold_met=False,
        )
        d = ev.to_dict()
        assert d["verdict"] == "PARTIAL"
        assert d["score"] == 0.6
        assert d["dimension_scores"]["correctness"] == 0.7
        assert d["feedback"] == "Missing details"
        assert d["pass_threshold_met"] is False

    def test_to_dict_fail_verdict(self) -> None:
        ev = JudgeEvaluation(
            verdict=JudgeVerdict.FAIL,
            score=0.0,
            dimension_scores={},
            feedback="Error",
            pass_threshold_met=False,
        )
        assert ev.to_dict()["verdict"] == "FAIL"
        assert ev.to_dict()["dimension_scores"] == {}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Test module-level constants."""

    def test_rubrics_has_expected_keys(self) -> None:
        assert "trade_signal" in TASK_TYPE_RUBRICS
        assert "content" in TASK_TYPE_RUBRICS
        assert "code_review" in TASK_TYPE_RUBRICS
        assert "default" in TASK_TYPE_RUBRICS

    def test_rubrics_values_are_strings(self) -> None:
        for key, val in TASK_TYPE_RUBRICS.items():
            assert isinstance(val, str), f"Rubric {key} is not a string"

    def test_system_prompt_is_nonempty(self) -> None:
        assert len(JUDGE_SYSTEM_PROMPT) > 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_api_response(payload: dict[str, Any]) -> MagicMock:
    """Create a mock Anthropic messages.create response."""
    text_block = MagicMock()
    text_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [text_block]
    return response


def _default_payload(
    verdict: str = "PASS",
    score: float = 0.85,
) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "score": score,
        "dimension_scores": {
            "correctness": 0.9,
            "completeness": 0.8,
            "reasoning_quality": 0.85,
            "actionability": 0.85,
        },
        "feedback": "Good output with solid reasoning.",
        "pass_threshold_met": True,
    }


def _make_agent() -> tuple[JudgeAgent, MagicMock]:
    """Create a JudgeAgent with a mocked Anthropic client."""
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        agent = JudgeAgent(api_key="sk-test")
    return agent, mock_client


# ---------------------------------------------------------------------------
# JudgeAgent.__init__
# ---------------------------------------------------------------------------


class TestJudgeAgentInit:
    """Test JudgeAgent construction."""

    def test_creates_client(self) -> None:
        with patch("anthropic.Anthropic") as mock_cls:
            JudgeAgent(api_key="sk-test")
            mock_cls.assert_called_once_with(api_key="sk-test")

    def test_default_model(self) -> None:
        with patch("anthropic.Anthropic"):
            agent = JudgeAgent()
            assert agent._model == "claude-haiku-3-5-20241022"

    def test_custom_model(self) -> None:
        with patch("anthropic.Anthropic"):
            agent = JudgeAgent(model="claude-sonnet-4-6")
            assert agent._model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# JudgeAgent.evaluate — happy path
# ---------------------------------------------------------------------------


class TestEvaluateHappyPath:
    """Test successful evaluate calls."""

    def test_pass_verdict(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload("PASS", 0.85)
        )

        result = agent.evaluate(
            task="Write a tutorial",
            task_type="content",
            output="Here is a tutorial...",
        )

        assert result.verdict == JudgeVerdict.PASS
        assert result.score == 0.85
        assert result.pass_threshold_met is True
        assert "correctness" in result.dimension_scores

    def test_fail_verdict(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload("FAIL", 0.3)
        )

        result = agent.evaluate(
            task="Analyze AAPL", task_type="trade_signal", output="Buy"
        )

        assert result.verdict == JudgeVerdict.FAIL
        assert result.score == 0.3

    def test_partial_verdict(self) -> None:
        agent, mock_client = _make_agent()
        payload = _default_payload("PARTIAL", 0.6)
        payload["pass_threshold_met"] = False
        mock_client.messages.create.return_value = _mock_api_response(payload)

        result = agent.evaluate(
            task="Review PR", task_type="code_review", output="LGTM"
        )

        assert result.verdict == JudgeVerdict.PARTIAL
        assert result.pass_threshold_met is False

    def test_uses_content_rubric(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload()
        )

        agent.evaluate(task="Write post", task_type="content", output="Post text")

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        # Content rubric mentions "platform"
        assert "platform" in user_msg.lower()

    def test_uses_default_rubric_for_unknown_type(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload()
        )

        agent.evaluate(
            task="Unknown task", task_type="mystery_type", output="Some output"
        )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        # Default rubric mentions "general tasks"
        assert "general tasks" in user_msg.lower()

    def test_custom_rubric_overrides_default(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload()
        )

        custom = "Check that output contains exactly 3 bullet points."
        agent.evaluate(
            task="Summarize", task_type="content", output="...", custom_rubric=custom
        )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "3 bullet points" in user_msg

    def test_api_called_with_correct_params(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response(
            _default_payload()
        )

        agent.evaluate(task="Test task", task_type="default", output="Test output")

        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-haiku-3-5-20241022"
        assert call_args["max_tokens"] == 1024
        assert call_args["temperature"] == 0.0
        assert call_args["system"] == JUDGE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# JudgeAgent.evaluate — error handling
# ---------------------------------------------------------------------------


class TestEvaluateErrors:
    """Test error handling in evaluate."""

    def test_json_decode_error(self) -> None:
        agent, mock_client = _make_agent()
        text_block = MagicMock()
        text_block.text = "This is not JSON at all"
        response = MagicMock()
        response.content = [text_block]
        mock_client.messages.create.return_value = response

        result = agent.evaluate(task="Test", task_type="default", output="Output")

        assert result.verdict == JudgeVerdict.FAIL
        assert result.score == 0.0
        assert "invalid JSON" in result.feedback

    def test_api_exception(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.side_effect = RuntimeError("API down")

        result = agent.evaluate(task="Test", task_type="default", output="Output")

        assert result.verdict == JudgeVerdict.FAIL
        assert result.score == 0.0
        assert "API down" in result.feedback

    def test_unknown_verdict_falls_back_to_fail(self) -> None:
        agent, mock_client = _make_agent()
        payload = _default_payload()
        payload["verdict"] = "UNKNOWN_VERDICT"
        mock_client.messages.create.return_value = _mock_api_response(payload)

        result = agent.evaluate(task="Test", task_type="default", output="Output")

        assert result.verdict == JudgeVerdict.FAIL

    def test_missing_fields_use_defaults(self) -> None:
        agent, mock_client = _make_agent()
        mock_client.messages.create.return_value = _mock_api_response({})

        result = agent.evaluate(task="Test", task_type="default", output="Output")

        assert result.verdict == JudgeVerdict.FAIL  # default "FAIL"
        assert result.score == 0.0
        assert result.dimension_scores == {}
        assert result.feedback == "No feedback provided"
        assert result.pass_threshold_met is False

    def test_empty_response_content(self) -> None:
        agent, mock_client = _make_agent()
        response = MagicMock()
        response.content = []  # No blocks
        mock_client.messages.create.return_value = response

        result = agent.evaluate(task="Test", task_type="default", output="Output")

        # Empty string -> JSONDecodeError
        assert result.verdict == JudgeVerdict.FAIL
        assert "invalid JSON" in result.feedback


# ---------------------------------------------------------------------------
# JudgeAgent.batch_evaluate
# ---------------------------------------------------------------------------


class TestBatchEvaluate:
    """Test batch_evaluate method."""

    def test_evaluates_all_items(self) -> None:
        agent, mock_client = _make_agent()
        responses = [
            _mock_api_response(_default_payload("PASS", 0.9)),
            _mock_api_response(_default_payload("FAIL", 0.3)),
            _mock_api_response(_default_payload("PARTIAL", 0.6)),
        ]
        mock_client.messages.create.side_effect = responses

        items = [
            {"task": "Task 1", "task_type": "content", "output": "Output 1"},
            {"task": "Task 2", "task_type": "trade_signal", "output": "Output 2"},
            {"task": "Task 3", "task_type": "code_review", "output": "Output 3"},
        ]
        results = agent.batch_evaluate(items)

        assert len(results) == 3
        assert results[0].verdict == JudgeVerdict.PASS
        assert results[1].verdict == JudgeVerdict.FAIL
        assert results[2].verdict == JudgeVerdict.PARTIAL

    def test_empty_batch(self) -> None:
        agent, _ = _make_agent()
        results = agent.batch_evaluate([])
        assert results == []

    def test_batch_with_api_error(self) -> None:
        agent, mock_client = _make_agent()
        responses = [
            _mock_api_response(_default_payload("PASS", 0.9)),
            RuntimeError("timeout"),  # Second call fails
        ]
        mock_client.messages.create.side_effect = responses

        items = [
            {"task": "Task 1", "task_type": "content", "output": "Output 1"},
            {"task": "Task 2", "task_type": "content", "output": "Output 2"},
        ]
        results = agent.batch_evaluate(items)

        assert len(results) == 2
        assert results[0].verdict == JudgeVerdict.PASS
        assert results[1].verdict == JudgeVerdict.FAIL  # error -> FAIL fallback
