"""Unit tests for holus.integrations.claude_api.client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from holus.integrations.claude_api.client import (
    MODEL_MAP,
    PRICING,
    CachedPrompt,
    HolusClaudeClient,
    define_tool,
    handle_tool_loop,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    text: str = "ok",
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 80,
    cache_write: int = 20,
    tool_calls: list | None = None,
):
    """Build a mock anthropic Message."""
    response = MagicMock()
    response.stop_reason = stop_reason

    blocks = []
    if text:
        tb = MagicMock()
        tb.type = "text"
        tb.text = text
        blocks.append(tb)
    if tool_calls:
        for tc in tool_calls:
            b = MagicMock()
            b.type = "tool_use"
            b.name = tc["name"]
            b.input = tc.get("input", {})
            b.id = tc.get("id", "tool_123")
            blocks.append(b)

    response.content = blocks
    response.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
    )
    return response


def _make_prompt(**kwargs) -> CachedPrompt:
    defaults = {"system_prompt": "You are a test assistant."}
    defaults.update(kwargs)
    return CachedPrompt(**defaults)


# ---------------------------------------------------------------------------
# CachedPrompt
# ---------------------------------------------------------------------------


class TestCachedPromptBuildSystemBlocks:
    def test_system_prompt_only_one_block(self):
        cp = _make_prompt()
        blocks = cp.build_system_blocks()
        assert len(blocks) == 1
        assert blocks[0]["text"] == "You are a test assistant."

    def test_with_persistent_context_two_blocks(self):
        cp = _make_prompt(persistent_context="Brand context here")
        blocks = cp.build_system_blocks()
        assert len(blocks) == 2
        assert blocks[1]["text"] == "Brand context here"

    def test_empty_persistent_context_one_block(self):
        cp = _make_prompt(persistent_context="")
        blocks = cp.build_system_blocks()
        assert len(blocks) == 1

    def test_cache_control_markers_present(self):
        cp = _make_prompt(persistent_context="ctx")
        blocks = cp.build_system_blocks()
        for block in blocks:
            assert block["cache_control"] == {"type": "ephemeral"}

    def test_block_types_are_text(self):
        cp = _make_prompt(persistent_context="ctx")
        blocks = cp.build_system_blocks()
        for block in blocks:
            assert block["type"] == "text"


class TestCachedPromptBuildToolsWithCache:
    def test_empty_tools_returns_empty(self):
        cp = _make_prompt(tools=[])
        assert cp.build_tools_with_cache() == []

    def test_cache_control_on_last_tool_only(self):
        tools = [
            {"name": "tool_a", "description": "A"},
            {"name": "tool_b", "description": "B"},
        ]
        cp = _make_prompt(tools=tools)
        result = cp.build_tools_with_cache()
        assert "cache_control" not in result[0]
        assert result[1]["cache_control"] == {"type": "ephemeral"}

    def test_single_tool_gets_cache_control(self):
        cp = _make_prompt(tools=[{"name": "t", "description": "d"}])
        result = cp.build_tools_with_cache()
        assert len(result) == 1
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_does_not_mutate_original_tools(self):
        original = [{"name": "a"}, {"name": "b"}]
        cp = _make_prompt(tools=original)
        cp.build_tools_with_cache()
        # Original should not have cache_control added
        assert "cache_control" not in original[0]
        assert "cache_control" not in original[1]


# ---------------------------------------------------------------------------
# HolusClaudeClient — call()
# ---------------------------------------------------------------------------


class TestClientCall:
    @pytest.fixture
    def client(self):
        with patch("holus.integrations.claude_api.client.anthropic.Anthropic"):
            c = HolusClaudeClient(api_key="sk-test")
            c.client = MagicMock()
            c.client.messages.create.return_value = _make_response()
            return c

    def test_strategic_routes_to_opus(self, client):
        cp = _make_prompt()
        client.call(cp, [{"role": "user", "content": "hi"}], tier="strategic")
        kwargs = client.client.messages.create.call_args[1]
        assert kwargs["model"] == MODEL_MAP["strategic"]

    def test_operational_routes_to_sonnet(self, client):
        cp = _make_prompt()
        client.call(cp, [{"role": "user", "content": "hi"}], tier="operational")
        kwargs = client.client.messages.create.call_args[1]
        assert kwargs["model"] == MODEL_MAP["operational"]

    def test_classification_routes_to_haiku(self, client):
        cp = _make_prompt()
        client.call(cp, [{"role": "user", "content": "hi"}], tier="classification")
        kwargs = client.client.messages.create.call_args[1]
        assert kwargs["model"] == MODEL_MAP["classification"]

    def test_tools_passed_when_present(self, client):
        tools = [{"name": "search", "description": "Search"}]
        cp = _make_prompt(tools=tools)
        client.call(cp, [{"role": "user", "content": "hi"}])
        kwargs = client.client.messages.create.call_args[1]
        assert "tools" in kwargs
        assert len(kwargs["tools"]) == 1

    def test_no_tools_kwarg_when_empty(self, client):
        cp = _make_prompt(tools=[])
        client.call(cp, [{"role": "user", "content": "hi"}])
        kwargs = client.client.messages.create.call_args[1]
        assert "tools" not in kwargs

    def test_extended_thinking_strategic_only(self, client):
        cp = _make_prompt()
        client.call(
            cp,
            [{"role": "user", "content": "think hard"}],
            tier="strategic",
            enable_thinking=True,
            thinking_budget=5000,
        )
        kwargs = client.client.messages.create.call_args[1]
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 5000}
        assert kwargs["temperature"] == 1.0

    def test_extended_thinking_ignored_for_operational(self, client):
        cp = _make_prompt()
        client.call(
            cp,
            [{"role": "user", "content": "think"}],
            tier="operational",
            enable_thinking=True,
        )
        kwargs = client.client.messages.create.call_args[1]
        assert "thinking" not in kwargs

    def test_cost_tracked_after_call(self, client):
        cp = _make_prompt()
        client.call(cp, [{"role": "user", "content": "hi"}], agent_id="test-agent")
        assert len(client._cost_log) == 1
        assert client._cost_log[0]["agent_id"] == "test-agent"


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------


class TestCostTracking:
    @pytest.fixture
    def client(self):
        with patch("holus.integrations.claude_api.client.anthropic.Anthropic"):
            return HolusClaudeClient(api_key="sk-test")

    def test_track_cost_records_entry(self, client):
        response = _make_response(
            input_tokens=1000,
            output_tokens=500,
            cache_read=200,
            cache_write=100,
        )
        model = "claude-sonnet-4-5-20250514"
        client._track_cost(response, model, "marketing")
        assert len(client._cost_log) == 1
        entry = client._cost_log[0]
        assert entry["agent_id"] == "marketing"
        assert entry["model"] == model
        assert entry["input_tokens"] == 1000
        assert entry["output_tokens"] == 500
        assert entry["cache_read_tokens"] == 200
        assert entry["cache_write_tokens"] == 100
        assert entry["cost_usd"] > 0

    def test_track_cost_handles_missing_cache_attrs(self, client):
        response = MagicMock()
        response.usage = MagicMock(spec=["input_tokens", "output_tokens"])
        response.usage.input_tokens = 500
        response.usage.output_tokens = 100
        # cache attrs don't exist — getattr should return 0
        del response.usage.cache_read_input_tokens
        del response.usage.cache_creation_input_tokens
        client._track_cost(response, "claude-sonnet-4-5-20250514", "test")
        assert len(client._cost_log) == 1
        assert client._cost_log[0]["cache_read_tokens"] == 0
        assert client._cost_log[0]["cache_write_tokens"] == 0

    def test_track_cost_unknown_model_zero_pricing(self, client):
        response = _make_response()
        client._track_cost(response, "unknown-model-v99", "test")
        assert client._cost_log[0]["cost_usd"] == 0.0

    def test_get_costs_filters_by_agent(self, client):
        r = _make_response()
        client._track_cost(r, "claude-sonnet-4-5-20250514", "agent-a")
        client._track_cost(r, "claude-sonnet-4-5-20250514", "agent-b")
        client._track_cost(r, "claude-sonnet-4-5-20250514", "agent-a")
        assert len(client.get_costs("agent-a")) == 2
        assert len(client.get_costs("agent-b")) == 1

    def test_get_costs_no_filter_returns_all(self, client):
        r = _make_response()
        client._track_cost(r, "claude-sonnet-4-5-20250514", "a")
        client._track_cost(r, "claude-sonnet-4-5-20250514", "b")
        assert len(client.get_costs()) == 2

    def test_total_cost_sums_correctly(self, client):
        r = _make_response(input_tokens=0, output_tokens=0, cache_read=0, cache_write=0)
        client._track_cost(r, "claude-sonnet-4-5-20250514", "a")
        client._track_cost(r, "claude-sonnet-4-5-20250514", "a")
        # Both have zero tokens → zero cost
        assert client.total_cost("a") == 0.0

    def test_total_cost_nonzero(self, client):
        r = _make_response(
            input_tokens=1_000_000, output_tokens=1_000_000, cache_read=0, cache_write=0
        )
        client._track_cost(r, "claude-sonnet-4-5-20250514", "x")
        # input: 1M * $3/M = $3, output: 1M * $15/M = $15, total $18
        assert client.total_cost("x") == pytest.approx(18.0, abs=0.01)


# ---------------------------------------------------------------------------
# define_tool
# ---------------------------------------------------------------------------


class TestDefineTool:
    def test_returns_correct_schema(self):
        tool = define_tool(
            name="search",
            description="Search the web",
            parameters={"query": {"type": "string"}},
            required=["query"],
        )
        assert tool["name"] == "search"
        assert tool["description"] == "Search the web"
        assert tool["input_schema"]["type"] == "object"
        assert tool["input_schema"]["required"] == ["query"]
        assert "query" in tool["input_schema"]["properties"]

    def test_required_defaults_to_empty_list(self):
        tool = define_tool(name="t", description="d", parameters={})
        assert tool["input_schema"]["required"] == []

    def test_with_multiple_parameters(self):
        tool = define_tool(
            name="gen",
            description="Generate",
            parameters={
                "prompt": {"type": "string"},
                "style": {"type": "string"},
            },
            required=["prompt"],
        )
        assert len(tool["input_schema"]["properties"]) == 2


# ---------------------------------------------------------------------------
# handle_tool_loop
# ---------------------------------------------------------------------------


class TestHandleToolLoop:
    @pytest.fixture
    def client(self):
        with patch("holus.integrations.claude_api.client.anthropic.Anthropic"):
            c = HolusClaudeClient(api_key="sk-test")
            c.client = MagicMock()
            return c

    def test_returns_text_on_end_turn(self, client):
        client.client.messages.create.return_value = _make_response(text="Final answer")
        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "What is 2+2?", {})
        assert result == "Final answer"

    def test_returns_empty_string_when_no_text_block(self, client):
        resp = MagicMock()
        resp.stop_reason = "end_turn"
        # Content blocks with no text attribute
        block = MagicMock(spec=[])
        resp.content = [block]
        client.client.messages.create.return_value = resp
        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "hi", {})
        assert result == ""

    def test_executes_tool_and_loops(self, client):
        # First call: tool_use, second call: end_turn with answer
        tool_response = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "calc", "input": {"x": 2}, "id": "t1"}],
        )
        # Remove the text block so only tool_use remains
        tool_response.content = [b for b in tool_response.content if b.type == "tool_use"]

        final_response = _make_response(text="Result is 4")
        client.client.messages.create.side_effect = [tool_response, final_response]

        def calc_handler(x):
            return x * 2

        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "calc 2", {"calc": calc_handler})
        assert result == "Result is 4"
        assert client.client.messages.create.call_count == 2

    def test_unknown_tool_returns_error_result(self, client):
        tool_resp = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "nonexistent", "input": {}, "id": "t1"}],
        )
        tool_resp.content = [b for b in tool_resp.content if b.type == "tool_use"]

        final = _make_response(text="ok")
        client.client.messages.create.side_effect = [tool_resp, final]

        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "hi", {})
        assert result == "ok"
        # Verify the error was sent back — check the second call's messages
        second_call_msgs = client.client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_msgs[-1]
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["is_error"] is True
        assert "Unknown tool" in tool_result_msg["content"][0]["content"]

    def test_tool_handler_exception_returns_error(self, client):
        tool_resp = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "broken", "input": {}, "id": "t1"}],
        )
        tool_resp.content = [b for b in tool_resp.content if b.type == "tool_use"]

        final = _make_response(text="recovered")
        client.client.messages.create.side_effect = [tool_resp, final]

        def broken_handler():
            raise ValueError("kaboom")

        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "hi", {"broken": broken_handler})
        assert result == "recovered"
        second_call_msgs = client.client.messages.create.call_args_list[1][1]["messages"]
        tool_result = second_call_msgs[-1]["content"][0]
        assert tool_result["is_error"] is True
        assert "kaboom" in tool_result["content"]

    def test_max_turns_reached(self, client):
        # Always return tool_use to exhaust turns
        tool_resp = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "loop", "input": {}, "id": "t1"}],
        )
        tool_resp.content = [b for b in tool_resp.content if b.type == "tool_use"]
        client.client.messages.create.return_value = tool_resp

        cp = _make_prompt()
        result = handle_tool_loop(client, cp, "hi", {"loop": lambda: "ok"}, max_turns=3)
        assert result == "Max tool turns reached without final response."
        assert client.client.messages.create.call_count == 3

    def test_tool_result_json_serialized(self, client):
        tool_resp = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "data", "input": {}, "id": "t1"}],
        )
        tool_resp.content = [b for b in tool_resp.content if b.type == "tool_use"]
        final = _make_response(text="done")
        client.client.messages.create.side_effect = [tool_resp, final]

        def data_handler():
            return {"key": "value", "num": 42}

        cp = _make_prompt()
        handle_tool_loop(client, cp, "hi", {"data": data_handler})
        second_call_msgs = client.client.messages.create.call_args_list[1][1]["messages"]
        tool_result = second_call_msgs[-1]["content"][0]
        parsed = json.loads(tool_result["content"])
        assert parsed == {"key": "value", "num": 42}

    def test_tool_result_string_not_double_serialized(self, client):
        tool_resp = _make_response(
            text="",
            stop_reason="tool_use",
            tool_calls=[{"name": "echo", "input": {}, "id": "t1"}],
        )
        tool_resp.content = [b for b in tool_resp.content if b.type == "tool_use"]
        final = _make_response(text="done")
        client.client.messages.create.side_effect = [tool_resp, final]

        cp = _make_prompt()
        handle_tool_loop(client, cp, "hi", {"echo": lambda: "plain text"})
        second_call_msgs = client.client.messages.create.call_args_list[1][1]["messages"]
        tool_result = second_call_msgs[-1]["content"][0]
        assert tool_result["content"] == "plain text"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_model_map_has_all_tiers(self):
        assert "strategic" in MODEL_MAP
        assert "operational" in MODEL_MAP
        assert "classification" in MODEL_MAP

    def test_pricing_covers_all_models(self):
        for tier, model_id in MODEL_MAP.items():
            assert model_id in PRICING, f"Missing pricing for {tier} ({model_id})"

    def test_pricing_tuples_have_four_elements(self):
        for model_id, prices in PRICING.items():
            assert len(prices) == 4, f"Pricing for {model_id} should have 4 elements"
            for p in prices:
                assert isinstance(p, float), f"Price should be float in {model_id}"
