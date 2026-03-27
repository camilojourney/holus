"""Unit tests for HolusClaudeClient — prompt caching, model routing, cost tracking, tool loop.

All tests mock the Anthropic client — no real API calls.
"""

from __future__ import annotations

from typing import Any
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


def _make_usage(
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_write: int = 0,
) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = cache_read
    usage.cache_creation_input_tokens = cache_write
    return usage


def _make_response(
    *,
    text: str = "Hello",
    stop_reason: str = "end_turn",
    usage: MagicMock | None = None,
    tool_use: dict[str, Any] | None = None,
) -> MagicMock:
    response = MagicMock()
    response.stop_reason = stop_reason
    response.usage = usage or _make_usage()

    if tool_use:
        block = MagicMock()
        block.type = "tool_use"
        block.name = tool_use["name"]
        block.input = tool_use.get("input", {})
        block.id = tool_use.get("id", "tool_123")
        response.content = [block]
    else:
        block = MagicMock()
        block.type = "text"
        block.text = text
        response.content = [block]

    return response


def _make_prompt(**kwargs: Any) -> CachedPrompt:
    defaults: dict[str, Any] = {
        "system_prompt": "You are a helpful assistant.",
    }
    defaults.update(kwargs)
    return CachedPrompt(**defaults)


# ---------------------------------------------------------------------------
# CachedPrompt tests
# ---------------------------------------------------------------------------


class TestCachedPrompt:
    """Tests for CachedPrompt build methods."""

    def test_build_system_blocks_single(self) -> None:
        prompt = _make_prompt()
        blocks = prompt.build_system_blocks()

        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert blocks[0]["text"] == "You are a helpful assistant."
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}

    def test_build_system_blocks_with_persistent_context(self) -> None:
        prompt = _make_prompt(persistent_context="Memory: user prefers short answers")
        blocks = prompt.build_system_blocks()

        assert len(blocks) == 2
        assert blocks[1]["text"] == "Memory: user prefers short answers"
        assert blocks[1]["cache_control"] == {"type": "ephemeral"}

    def test_build_system_blocks_empty_persistent_context(self) -> None:
        prompt = _make_prompt(persistent_context="")
        blocks = prompt.build_system_blocks()

        assert len(blocks) == 1

    def test_build_tools_with_cache_empty(self) -> None:
        prompt = _make_prompt(tools=[])
        assert prompt.build_tools_with_cache() == []

    def test_build_tools_with_cache_marks_last(self) -> None:
        tools = [
            {"name": "tool_a", "description": "A"},
            {"name": "tool_b", "description": "B"},
        ]
        prompt = _make_prompt(tools=tools)
        cached_tools = prompt.build_tools_with_cache()

        assert len(cached_tools) == 2
        # Only last tool has cache_control
        assert "cache_control" not in cached_tools[0]
        assert cached_tools[1]["cache_control"] == {"type": "ephemeral"}

    def test_build_tools_does_not_mutate_original(self) -> None:
        tools = [{"name": "tool_a", "description": "A"}]
        prompt = _make_prompt(tools=tools)
        prompt.build_tools_with_cache()

        # Original tools should not have cache_control
        assert "cache_control" not in tools[0]


# ---------------------------------------------------------------------------
# HolusClaudeClient tests
# ---------------------------------------------------------------------------


class TestHolusClaudeClient:
    """Tests for client initialization, call routing, and cost tracking."""

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_init_default(self, mock_anthropic_cls: MagicMock) -> None:
        client = HolusClaudeClient()
        mock_anthropic_cls.assert_called_once_with()
        assert client._model_map == dict(MODEL_MAP)

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_init_with_api_key_and_base_url(self, mock_anthropic_cls: MagicMock) -> None:
        HolusClaudeClient(api_key="sk-test", base_url="http://proxy:8080")
        mock_anthropic_cls.assert_called_once_with(api_key="sk-test", base_url="http://proxy:8080")

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_init_custom_model_map(self, mock_anthropic_cls: MagicMock) -> None:
        custom = {
            "strategic": "custom-opus",
            "operational": "custom-sonnet",
            "classification": "custom-haiku",
        }
        client = HolusClaudeClient(model_map=custom)
        assert client._model_map == custom

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_call_routes_to_correct_model(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        # Test strategic tier -> Opus
        client.call(prompt, [{"role": "user", "content": "test"}], tier="strategic")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"

        # Test operational tier -> Sonnet
        client.call(prompt, [{"role": "user", "content": "test"}], tier="operational")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_call_includes_tools_when_provided(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt(tools=[{"name": "search", "description": "Search"}])

        client.call(prompt, [{"role": "user", "content": "test"}])
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_call_no_tools_when_empty(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(prompt, [{"role": "user", "content": "test"}])
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_call_extended_thinking_strategic(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(
            prompt,
            [{"role": "user", "content": "think hard"}],
            tier="strategic",
            enable_thinking=True,
            thinking_budget=5000,
        )
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 5000}
        assert call_kwargs["temperature"] == 1.0  # Required for thinking

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_call_extended_thinking_non_strategic_ignored(
        self, mock_anthropic_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(
            prompt,
            [{"role": "user", "content": "test"}],
            tier="operational",
            enable_thinking=True,
        )
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "thinking" not in call_kwargs

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_cost_tracking_basic(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        usage = _make_usage(input_tokens=1000, output_tokens=500)
        mock_client.messages.create.return_value = _make_response(usage=usage)

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(prompt, [{"role": "user", "content": "test"}], agent_id="marketing")

        costs = client.get_costs()
        assert len(costs) == 1
        assert costs[0]["agent_id"] == "marketing"
        assert costs[0]["model"] == "claude-sonnet-4-6"
        assert costs[0]["input_tokens"] == 1000
        assert costs[0]["output_tokens"] == 500
        assert costs[0]["cost_usd"] > 0

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_cost_tracking_with_cache(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        usage = _make_usage(
            input_tokens=100,
            output_tokens=50,
            cache_read=5000,
            cache_write=2000,
        )
        mock_client.messages.create.return_value = _make_response(usage=usage)

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(prompt, [{"role": "user", "content": "test"}], agent_id="marketing")

        costs = client.get_costs()
        assert len(costs) == 1
        assert costs[0]["cache_read_tokens"] == 5000
        assert costs[0]["cache_write_tokens"] == 2000

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_cost_filter_by_agent(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(prompt, [{"role": "user", "content": "a"}], agent_id="marketing")
        client.call(prompt, [{"role": "user", "content": "b"}], agent_id="judge")
        client.call(prompt, [{"role": "user", "content": "c"}], agent_id="marketing")

        assert len(client.get_costs("marketing")) == 2
        assert len(client.get_costs("judge")) == 1
        assert len(client.get_costs()) == 3

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_total_cost(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response()

        client = HolusClaudeClient()
        prompt = _make_prompt()

        client.call(prompt, [{"role": "user", "content": "a"}])
        client.call(prompt, [{"role": "user", "content": "b"}])

        total = client.total_cost()
        assert total >= 0
        assert isinstance(total, float)


# ---------------------------------------------------------------------------
# Cost calculation tests
# ---------------------------------------------------------------------------


class TestCostCalculation:
    """Verify cost calculation math for different models."""

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_sonnet_cost_calculation(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # 1M input, 1M output at Sonnet rates: $3 + $15 = $18
        usage = _make_usage(input_tokens=1_000_000, output_tokens=1_000_000)
        mock_client.messages.create.return_value = _make_response(usage=usage)

        client = HolusClaudeClient()
        client.call(_make_prompt(), [{"role": "user", "content": "test"}], tier="operational")

        cost = client.get_costs()[0]["cost_usd"]
        assert cost == pytest.approx(18.0, abs=0.01)

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_opus_cost_calculation(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # 1M input, 1M output at Opus rates: $15 + $75 = $90
        usage = _make_usage(input_tokens=1_000_000, output_tokens=1_000_000)
        mock_client.messages.create.return_value = _make_response(usage=usage)

        client = HolusClaudeClient()
        client.call(_make_prompt(), [{"role": "user", "content": "test"}], tier="strategic")

        cost = client.get_costs()[0]["cost_usd"]
        assert cost == pytest.approx(90.0, abs=0.01)

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_cache_read_discount(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # 1M cache read at Sonnet ($0.30/M) vs 1M regular input ($3/M)
        usage = _make_usage(input_tokens=0, output_tokens=0, cache_read=1_000_000)
        mock_client.messages.create.return_value = _make_response(usage=usage)

        client = HolusClaudeClient()
        client.call(_make_prompt(), [{"role": "user", "content": "test"}], tier="operational")

        cost = client.get_costs()[0]["cost_usd"]
        assert cost == pytest.approx(0.30, abs=0.01)


# ---------------------------------------------------------------------------
# Batch API tests
# ---------------------------------------------------------------------------


class TestBatchAPI:
    """Tests for batch submit and poll."""

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_batch_submit(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.batches.create.return_value = MagicMock(id="batch_123")

        client = HolusClaudeClient()
        prompt = _make_prompt()

        result = client.batch_submit(
            [
                {
                    "custom_id": "req_1",
                    "cached_prompt": prompt,
                    "messages": [{"role": "user", "content": "a"}],
                },
                {
                    "custom_id": "req_2",
                    "cached_prompt": prompt,
                    "messages": [{"role": "user", "content": "b"}],
                },
            ]
        )

        assert result.id == "batch_123"
        call_kwargs = mock_client.messages.batches.create.call_args[1]
        assert len(call_kwargs["requests"]) == 2
        assert call_kwargs["requests"][0]["custom_id"] == "req_1"

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_batch_poll(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.batches.retrieve.return_value = MagicMock(
            id="batch_123", processing_status="ended"
        )

        client = HolusClaudeClient()
        result = client.batch_poll("batch_123")
        assert result.processing_status == "ended"

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_batch_results(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.batches.results.return_value = [
            MagicMock(custom_id="req_1"),
            MagicMock(custom_id="req_2"),
        ]

        client = HolusClaudeClient()
        results = client.batch_results("batch_123")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# define_tool helper tests
# ---------------------------------------------------------------------------


class TestDefineTool:
    """Tests for the define_tool helper."""

    def test_basic_tool(self) -> None:
        tool = define_tool(
            name="search",
            description="Search docs",
            parameters={"query": {"type": "string", "description": "Query"}},
            required=["query"],
        )
        assert tool["name"] == "search"
        assert tool["description"] == "Search docs"
        assert tool["input_schema"]["type"] == "object"
        assert "query" in tool["input_schema"]["properties"]
        assert tool["input_schema"]["required"] == ["query"]

    def test_no_required_defaults_empty(self) -> None:
        tool = define_tool(name="t", description="d", parameters={})
        assert tool["input_schema"]["required"] == []


# ---------------------------------------------------------------------------
# Tool loop tests
# ---------------------------------------------------------------------------


class TestHandleToolLoop:
    """Tests for the multi-turn tool-use loop."""

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_simple_text_response(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_response(text="Done!")

        client = HolusClaudeClient()
        result = handle_tool_loop(
            client=client,
            cached_prompt=_make_prompt(),
            initial_message="do something",
            tool_handlers={},
        )
        assert result == "Done!"

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_tool_call_then_response(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # First call: tool use, second call: text response
        tool_response = _make_response(
            stop_reason="tool_use",
            tool_use={"name": "search", "input": {"query": "test"}, "id": "tu_1"},
        )
        text_response = _make_response(text="Found it!")

        mock_client.messages.create.side_effect = [tool_response, text_response]

        client = HolusClaudeClient()
        result = handle_tool_loop(
            client=client,
            cached_prompt=_make_prompt(),
            initial_message="search for test",
            tool_handlers={"search": lambda query: f"result for {query}"},
        )

        assert result == "Found it!"
        assert mock_client.messages.create.call_count == 2

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_tool_handler_error(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_response = _make_response(
            stop_reason="tool_use",
            tool_use={"name": "failing_tool", "input": {}, "id": "tu_1"},
        )
        text_response = _make_response(text="Handled error")

        mock_client.messages.create.side_effect = [tool_response, text_response]

        def bad_handler(**kwargs: Any) -> str:
            msg = "Something went wrong"
            raise ValueError(msg)

        client = HolusClaudeClient()
        result = handle_tool_loop(
            client=client,
            cached_prompt=_make_prompt(),
            initial_message="try this",
            tool_handlers={"failing_tool": bad_handler},
        )

        assert result == "Handled error"
        # Verify the error was passed back as tool_result
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["is_error"] is True

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_unknown_tool(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_response = _make_response(
            stop_reason="tool_use",
            tool_use={"name": "nonexistent", "input": {}, "id": "tu_1"},
        )
        text_response = _make_response(text="OK")

        mock_client.messages.create.side_effect = [tool_response, text_response]

        client = HolusClaudeClient()
        result = handle_tool_loop(
            client=client,
            cached_prompt=_make_prompt(),
            initial_message="test",
            tool_handlers={},
        )

        assert result == "OK"
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]
        assert "Unknown tool" in tool_result_msg["content"][0]["content"]

    @patch("holus.integrations.claude_api.client.anthropic.Anthropic")
    def test_max_turns_limit(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Always return tool_use — never resolves
        tool_response = _make_response(
            stop_reason="tool_use",
            tool_use={"name": "loop_tool", "input": {}, "id": "tu_1"},
        )
        mock_client.messages.create.return_value = tool_response

        client = HolusClaudeClient()
        result = handle_tool_loop(
            client=client,
            cached_prompt=_make_prompt(),
            initial_message="infinite loop",
            tool_handlers={"loop_tool": lambda: "again"},
            max_turns=3,
        )

        assert "Max tool turns reached" in result
        assert mock_client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# Pricing table tests
# ---------------------------------------------------------------------------


class TestPricingTable:
    """Verify pricing table structure."""

    def test_all_models_have_pricing(self) -> None:
        for model in MODEL_MAP.values():
            assert model in PRICING, f"Missing pricing for {model}"

    def test_pricing_tuple_structure(self) -> None:
        for model, prices in PRICING.items():
            assert len(prices) == 4, f"{model} pricing must have 4 values"
            assert all(p >= 0 for p in prices), f"{model} has negative pricing"

    def test_cache_read_cheaper_than_input(self) -> None:
        for model, prices in PRICING.items():
            input_price, _cache_write, cache_read, _output = prices
            assert cache_read <= input_price, f"{model} cache_read should be <= input"
