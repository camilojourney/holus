"""Tests for holus.self_improvement.reflexion."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from holus.self_improvement.reflexion import (
    REFLECTION_PROMPT,
    ReflectionMemoryManager,
    ReflexionLoop,
    ReflexionState,
    evaluate_node,
    execute_node,
    finish_fail,
    finish_pass,
    reflect_node,
    should_retry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides: Any) -> ReflexionState:
    """Create a minimal ReflexionState with sensible defaults."""
    base: ReflexionState = {
        "task": "Write a product launch plan",
        "task_type": "strategy_decision",
        "agent_id": "test-agent",
        "attempt": 0,
        "max_attempts": 3,
        "output": "",
        "evaluation": {},
        "reflections": [],
        "episodic_memory": [],
        "final_output": "",
        "final_verdict": "",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _mock_claude_response(text: str) -> MagicMock:
    """Build a mock Claude API response with a single text block."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


# ---------------------------------------------------------------------------
# should_retry (routing logic)
# ---------------------------------------------------------------------------


class TestShouldRetry:
    """Test the conditional routing node."""

    def test_pass_finishes(self) -> None:
        state = _make_state(evaluation={"verdict": "PASS"}, attempt=1)
        assert should_retry(state) == "finish_pass"

    def test_fail_at_max_attempts_finishes(self) -> None:
        state = _make_state(evaluation={"verdict": "FAIL"}, attempt=3, max_attempts=3)
        assert should_retry(state) == "finish_fail"

    def test_fail_with_retries_left_reflects(self) -> None:
        state = _make_state(evaluation={"verdict": "FAIL"}, attempt=1, max_attempts=3)
        assert should_retry(state) == "reflect"

    def test_partial_with_retries_reflects(self) -> None:
        state = _make_state(evaluation={"verdict": "PARTIAL"}, attempt=1, max_attempts=3)
        assert should_retry(state) == "reflect"

    def test_missing_evaluation_defaults_to_fail(self) -> None:
        state = _make_state(evaluation={}, attempt=1, max_attempts=3)
        assert should_retry(state) == "reflect"

    def test_missing_evaluation_at_max_finishes_fail(self) -> None:
        state = _make_state(evaluation={}, attempt=3, max_attempts=3)
        assert should_retry(state) == "finish_fail"


# ---------------------------------------------------------------------------
# finish_pass / finish_fail
# ---------------------------------------------------------------------------


class TestFinishNodes:
    """Test terminal nodes."""

    def test_finish_pass_returns_output_and_verdict(self) -> None:
        state = _make_state(output="Great plan!")
        result = finish_pass(state)
        assert result["final_output"] == "Great plan!"
        assert result["final_verdict"] == "PASS"

    def test_finish_fail_returns_output_and_verdict(self) -> None:
        state = _make_state(output="Bad attempt", evaluation={"verdict": "FAIL"})
        result = finish_fail(state)
        assert result["final_output"] == "Bad attempt"
        assert result["final_verdict"] == "FAIL"

    def test_finish_fail_defaults_verdict_when_missing(self) -> None:
        state = _make_state(output="No eval", evaluation={})
        result = finish_fail(state)
        assert result["final_verdict"] == "FAIL"

    def test_finish_fail_preserves_partial_verdict(self) -> None:
        state = _make_state(output="Meh", evaluation={"verdict": "PARTIAL"})
        result = finish_fail(state)
        assert result["final_verdict"] == "PARTIAL"


# ---------------------------------------------------------------------------
# execute_node
# ---------------------------------------------------------------------------


class TestExecuteNode:
    """Test the execution node (calls Claude with reflections context)."""

    def test_basic_execution_without_memory(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("Plan output")
        prompt = MagicMock()
        state = _make_state()

        result = execute_node(state, client, prompt, "operational")

        assert result["output"] == "Plan output"
        assert result["attempt"] == 1
        client.call.assert_called_once()

    def test_episodic_memory_included_in_context(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("output")
        prompt = MagicMock()
        state = _make_state(episodic_memory=["Past lesson 1", "Past lesson 2"])

        execute_node(state, client, prompt, "operational")

        call_args = client.call.call_args
        msg = call_args.kwargs["messages"][0]["content"]
        assert "Lessons from Previous Similar Tasks" in msg
        assert "Past lesson 1" in msg
        assert "Past lesson 2" in msg

    def test_reflections_included_in_context(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("better output")
        prompt = MagicMock()
        state = _make_state(
            reflections=["I should be more specific"],
            attempt=1,
        )

        execute_node(state, client, prompt, "strategic")

        call_args = client.call.call_args
        msg = call_args.kwargs["messages"][0]["content"]
        assert "Reflections from Previous Attempts" in msg
        assert "I should be more specific" in msg

    def test_episodic_memory_limited_to_5(self) -> None:
        """Only last 5 episodic memories should be included."""
        client = MagicMock()
        client.call.return_value = _mock_claude_response("output")
        prompt = MagicMock()
        memories = [f"Memory {i}" for i in range(10)]
        state = _make_state(episodic_memory=memories)

        execute_node(state, client, prompt, "operational")

        msg = client.call.call_args.kwargs["messages"][0]["content"]
        # Last 5 = Memory 5..9
        assert "Memory 5" in msg
        assert "Memory 9" in msg
        assert "Memory 0" not in msg

    def test_attempt_incremented(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("x")
        state = _make_state(attempt=2)

        result = execute_node(state, client, MagicMock(), "operational")
        assert result["attempt"] == 3


# ---------------------------------------------------------------------------
# evaluate_node
# ---------------------------------------------------------------------------


class TestEvaluateNode:
    """Test the evaluation node (wraps JudgeAgent)."""

    @patch("holus.self_improvement.judge.JudgeAgent")
    def test_calls_judge_and_returns_dict(self, mock_judge_cls: MagicMock) -> None:
        mock_eval = MagicMock()
        mock_eval.to_dict.return_value = {
            "verdict": "PASS",
            "score": 0.85,
            "feedback": "Well done",
        }
        mock_judge_cls.return_value.evaluate.return_value = mock_eval
        client = MagicMock()
        state = _make_state(output="Some output")

        result = evaluate_node(state, client)

        assert result["evaluation"]["verdict"] == "PASS"
        assert result["evaluation"]["score"] == 0.85
        mock_judge_cls.return_value.evaluate.assert_called_once_with(
            task="Write a product launch plan",
            task_type="strategy_decision",
            output="Some output",
        )


# ---------------------------------------------------------------------------
# reflect_node
# ---------------------------------------------------------------------------


class TestReflectNode:
    """Test the reflection node (generates verbal reflection)."""

    def test_generates_reflection(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("I need better hooks")
        state = _make_state(
            output="Weak plan",
            evaluation={"verdict": "FAIL", "score": 0.3, "feedback": "Too vague"},
        )

        result = reflect_node(state, client)

        assert len(result["reflections"]) == 1
        assert result["reflections"][0] == "I need better hooks"

    def test_appends_to_existing_reflections(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("Second reflection")
        state = _make_state(
            reflections=["First reflection"],
            output="Still weak",
            evaluation={"verdict": "FAIL", "score": 0.4, "feedback": "Not actionable"},
        )

        result = reflect_node(state, client)

        assert len(result["reflections"]) == 2
        assert result["reflections"][0] == "First reflection"
        assert result["reflections"][1] == "Second reflection"

    def test_uses_operational_tier(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("insight")
        state = _make_state(evaluation={})

        reflect_node(state, client)

        call_args = client.call.call_args
        assert call_args.kwargs["tier"] == "operational"

    def test_prompt_includes_evaluation_data(self) -> None:
        client = MagicMock()
        client.call.return_value = _mock_claude_response("insight")
        state = _make_state(
            output="My attempt",
            evaluation={"verdict": "PARTIAL", "score": 0.5, "feedback": "Missing CTA"},
        )

        reflect_node(state, client)

        msg = client.call.call_args.kwargs["messages"][0]["content"]
        assert "PARTIAL" in msg
        assert "0.5" in msg
        assert "Missing CTA" in msg


# ---------------------------------------------------------------------------
# REFLECTION_PROMPT constant
# ---------------------------------------------------------------------------


class TestReflectionPrompt:
    """Test the reflection prompt template."""

    def test_has_required_placeholders(self) -> None:
        for key in ("task", "output", "verdict", "score", "feedback", "previous_reflections"):
            assert f"{{{key}}}" in REFLECTION_PROMPT

    def test_format_works(self) -> None:
        result = REFLECTION_PROMPT.format(
            task="Test task",
            output="Test output",
            verdict="FAIL",
            score=0.2,
            feedback="Bad",
            previous_reflections="None",
        )
        assert "Test task" in result
        assert "Test output" in result


# ---------------------------------------------------------------------------
# ReflexionLoop
# ---------------------------------------------------------------------------


class TestReflexionLoop:
    """Test the ReflexionLoop class (graph construction, init)."""

    def test_init_stores_params(self) -> None:
        client = MagicMock()
        prompt = MagicMock()
        loop = ReflexionLoop(client, prompt, tier="strategic")
        assert loop._client is client
        assert loop._agent_prompt is prompt
        assert loop._tier == "strategic"

    def test_default_tier_is_operational(self) -> None:
        loop = ReflexionLoop(MagicMock(), MagicMock())
        assert loop._tier == "operational"

    def test_build_graph_returns_state_graph(self) -> None:
        from langgraph.graph import StateGraph

        loop = ReflexionLoop(MagicMock(), MagicMock())
        graph = loop.build_graph()
        assert isinstance(graph, StateGraph)

    def test_build_graph_has_all_nodes(self) -> None:
        loop = ReflexionLoop(MagicMock(), MagicMock())
        graph = loop.build_graph()
        node_names = set(graph.nodes.keys())
        expected = {"execute", "evaluate", "reflect", "finish_pass", "finish_fail"}
        assert expected.issubset(node_names)


# ---------------------------------------------------------------------------
# ReflectionMemoryManager
# ---------------------------------------------------------------------------


class TestReflectionMemoryManager:
    """Test the Mem0-backed reflection memory manager."""

    def test_store_reflection_calls_mem0_add(self) -> None:
        mem0 = MagicMock()
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        mgr.store_reflection(
            agent_id="marketing",
            task_type="strategy_decision",
            reflection="Need better hooks",
            task_summary="Write launch plan",
            score=0.4,
        )

        mem0.add.assert_called_once()
        call_args = mem0.add.call_args
        text = call_args.args[0]
        assert "strategy_decision" in text
        assert "Need better hooks" in text
        assert "0.40" in text

    def test_store_reflection_metadata(self) -> None:
        mem0 = MagicMock()
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        mgr.store_reflection(
            agent_id="marketing",
            task_type="content_generation",
            reflection="insight",
            task_summary="task",
            score=0.7,
        )

        metadata = mem0.add.call_args.kwargs["metadata"]
        assert metadata["type"] == "reflection"
        assert metadata["task_type"] == "content_generation"
        assert metadata["score"] == 0.7

    def test_retrieve_relevant_returns_memories(self) -> None:
        mem0 = MagicMock()
        mem0.search.return_value = [
            {"memory": "Past reflection 1"},
            {"memory": "Past reflection 2"},
        ]
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        results = mgr.retrieve_relevant("Launch plan for Pilaster")

        assert len(results) == 2
        assert results[0] == "Past reflection 1"
        mem0.search.assert_called_once_with(query="Launch plan for Pilaster", limit=5)

    def test_retrieve_relevant_filters_empty_memories(self) -> None:
        mem0 = MagicMock()
        mem0.search.return_value = [
            {"memory": "Good one"},
            {"memory": ""},
            {},
        ]
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        results = mgr.retrieve_relevant("task")
        assert results == ["Good one"]

    def test_get_failure_patterns_returns_failures_above_threshold(self) -> None:
        mem0 = MagicMock()
        failures = [
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.3,
                }
            },
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.2,
                }
            },
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.1,
                }
            },
        ]
        mem0.get_all.return_value = failures
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        result = mgr.get_failure_patterns("strategy_decision", min_count=3)
        assert len(result) == 3

    def test_get_failure_patterns_empty_when_below_threshold(self) -> None:
        mem0 = MagicMock()
        mem0.get_all.return_value = [
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.3,
                }
            },
        ]
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        result = mgr.get_failure_patterns("strategy_decision", min_count=3)
        assert result == []

    def test_get_failure_patterns_filters_by_task_type(self) -> None:
        mem0 = MagicMock()
        mem0.get_all.return_value = [
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.2,
                }
            },
            {
                "metadata": {
                    "task_type": "content_generation",  # different type
                    "type": "reflection",
                    "score": 0.1,
                }
            },
            {
                "metadata": {
                    "task_type": "strategy_decision",
                    "type": "reflection",
                    "score": 0.3,
                }
            },
        ]
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        result = mgr.get_failure_patterns("strategy_decision", min_count=3)
        # Only 2 match strategy_decision, below min_count=3
        assert result == []

    def test_get_failure_patterns_ignores_passing_scores(self) -> None:
        mem0 = MagicMock()
        mem0.get_all.return_value = [
            {
                "metadata": {
                    "task_type": "x",
                    "type": "reflection",
                    "score": 0.8,  # passing score (>= 0.5)
                }
            },
            {
                "metadata": {
                    "task_type": "x",
                    "type": "reflection",
                    "score": 0.6,  # passing score
                }
            },
            {
                "metadata": {
                    "task_type": "x",
                    "type": "reflection",
                    "score": 0.3,  # failing
                }
            },
        ]
        mgr = ReflectionMemoryManager(mem0_client=mem0)

        result = mgr.get_failure_patterns("x", min_count=2)
        # Only 1 failure (score < 0.5), below min_count=2
        assert result == []
