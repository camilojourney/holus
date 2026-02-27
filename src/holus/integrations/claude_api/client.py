"""Central Claude API client for all Holus agents.

Handles:
  - Prompt caching (stable prefix + dynamic suffix architecture)
  - Model routing (Opus for strategic, Sonnet for operational, Haiku for classification)
  - Batch API for non-urgent tasks (50% discount, 24h SLA)
  - Cost tracking per agent
  - Tool use loop (multi-turn agentic execution)
  - Extended thinking support for complex reasoning

Pricing (per million tokens, as of Feb 2026):
  Opus 4:     $15 / $75  input/output  ($1.50 cache read, $3.75 cache write)
  Sonnet 4.5: $3 / $15   input/output  ($0.30 cache read, $0.75 cache write)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import anthropic

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ModelTier = Literal["strategic", "operational", "classification"]

MODEL_MAP: dict[ModelTier, str] = {
    "strategic": "claude-opus-4-20250514",
    "operational": "claude-sonnet-4-5-20250514",
    "classification": "claude-haiku-3-5-20241022",
}

# (input_regular, cache_write, cache_read, output)
PRICING: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-4-20250514": (15.0, 3.75, 1.50, 75.0),
    "claude-sonnet-4-5-20250514": (3.0, 0.75, 0.30, 15.0),
    "claude-haiku-3-5-20241022": (0.25, 0.03, 0.03, 1.25),
}


# ---------------------------------------------------------------------------
# Cached Prompt
# ---------------------------------------------------------------------------


@dataclass
class CachedPrompt:
    """A prompt structured for Anthropic's prompt caching.

    Architecture: stable_prefix (cached) + dynamic_suffix (per-call).

    The prefix includes the system prompt, tool definitions, and persistent
    memory (RAG results, CLAUDE.md context).  The suffix is the current task.

    Cache rules:
      - Minimum cacheable prefix: 1024 tokens (Sonnet), 2048 tokens (Opus).
      - TTL: 5 minutes, extended to 1 hour with regular cache hits.
      - ANY change to the prefix invalidates the cache -- keep dynamic data
        (timestamps, prices) in the user message, not the system prompt.
    """

    system_prompt: str
    tools: list[dict[str, Any]] = field(default_factory=list)
    persistent_context: str = ""

    def build_system_blocks(self) -> list[dict[str, Any]]:
        """Build system message blocks with ``cache_control`` markers."""
        blocks: list[dict[str, Any]] = []

        # Block 1: System prompt (most stable)
        blocks.append(
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        )

        # Block 2: Persistent context (changes less frequently than task)
        if self.persistent_context:
            blocks.append(
                {
                    "type": "text",
                    "text": self.persistent_context,
                    "cache_control": {"type": "ephemeral"},
                }
            )

        return blocks

    def build_tools_with_cache(self) -> list[dict[str, Any]]:
        """Return tool definitions with ``cache_control`` on the last tool."""
        if not self.tools:
            return []
        tools_copy = [dict(t) for t in self.tools]
        tools_copy[-1]["cache_control"] = {"type": "ephemeral"}
        return tools_copy


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class HolusClaudeClient:
    """Central Claude API client for all Holus agents."""

    def __init__(self, api_key: str | None = None) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self._cost_log: list[dict[str, Any]] = []

    # -- Synchronous call ----------------------------------------------------

    def call(
        self,
        cached_prompt: CachedPrompt,
        messages: list[dict[str, Any]],
        *,
        tier: ModelTier = "operational",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        enable_thinking: bool = False,
        thinking_budget: int = 10_000,
        agent_id: str = "unknown",
    ) -> anthropic.types.Message:
        """Make a Claude API call with prompt caching and model routing.

        Args:
            cached_prompt: Structured prompt with stable prefix.
            messages: Dynamic conversation messages (the suffix).
            tier: ``"strategic"`` (Opus), ``"operational"`` (Sonnet),
                  or ``"classification"`` (Haiku).
            max_tokens: Maximum output tokens.
            temperature: 0.0 for deterministic, higher for creative.
            enable_thinking: Enable extended thinking (chain-of-thought).
            thinking_budget: Maximum tokens for the thinking block.
            agent_id: For cost tracking and Langfuse attribution.
        """
        model = MODEL_MAP[tier]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": cached_prompt.build_system_blocks(),
            "messages": messages,
            "temperature": temperature,
        }

        # Tools
        tools = cached_prompt.build_tools_with_cache()
        if tools:
            kwargs["tools"] = tools

        # Extended thinking -- requires temperature=1.0
        if enable_thinking and tier == "strategic":
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }
            kwargs["temperature"] = 1.0

        response = self.client.messages.create(**kwargs)
        self._track_cost(response, model, agent_id)
        return response

    # -- Streaming call ------------------------------------------------------

    def call_streaming(
        self,
        cached_prompt: CachedPrompt,
        messages: list[dict[str, Any]],
        *,
        tier: ModelTier = "operational",
        max_tokens: int = 4096,
        agent_id: str = "unknown",
    ) -> Generator[Any, None, None]:
        """Streaming version for real-time output."""
        model = MODEL_MAP[tier]

        tools = cached_prompt.build_tools_with_cache()
        tools_arg = tools if tools else anthropic.NOT_GIVEN

        with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=cached_prompt.build_system_blocks(),
            messages=messages,
            tools=tools_arg,
        ) as stream:
            yield from stream
            response = stream.get_final_message()
            self._track_cost(response, model, agent_id)

    # -- Batch API -----------------------------------------------------------

    def batch_submit(
        self,
        requests: list[dict[str, Any]],
        *,
        tier: ModelTier = "operational",
    ) -> anthropic.types.MessageBatch:
        """Submit batch requests for 50% discount.  24-hour SLA.

        Each item in *requests* must have:
          - ``custom_id``
          - ``cached_prompt`` (a ``CachedPrompt``)
          - ``messages`` (list of message dicts)
          - optional ``max_tokens``
        """
        model = MODEL_MAP[tier]
        batch_items: list[dict[str, Any]] = []

        for req in requests:
            cp: CachedPrompt = req["cached_prompt"]
            batch_items.append(
                {
                    "custom_id": req["custom_id"],
                    "params": {
                        "model": model,
                        "max_tokens": req.get("max_tokens", 4096),
                        "system": cp.build_system_blocks(),
                        "messages": req["messages"],
                        "tools": cp.build_tools_with_cache() or [],
                    },
                }
            )

        return self.client.messages.batches.create(requests=batch_items)

    def batch_poll(self, batch_id: str) -> anthropic.types.MessageBatch:
        """Poll a batch for completion status."""
        return self.client.messages.batches.retrieve(batch_id)

    def batch_results(self, batch_id: str) -> list[Any]:
        """Retrieve results from a completed batch."""
        return list(self.client.messages.batches.results(batch_id))

    # -- Cost tracking -------------------------------------------------------

    def _track_cost(
        self,
        response: anthropic.types.Message,
        model: str,
        agent_id: str,
    ) -> None:
        """Record token usage and cost for Langfuse reporting."""
        usage = response.usage
        prices = PRICING.get(model, (0.0, 0.0, 0.0, 0.0))

        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

        input_cost = (
            (cache_read / 1_000_000) * prices[2]
            + (cache_write / 1_000_000) * prices[1]
            + (input_tokens / 1_000_000) * prices[0]
        )
        output_cost = (output_tokens / 1_000_000) * prices[3]

        entry = {
            "agent_id": agent_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "cost_usd": round(input_cost + output_cost, 6),
        }
        self._cost_log.append(entry)
        logger.debug("API cost: %s", entry)

    def get_costs(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        """Return cost logs, optionally filtered by agent."""
        if agent_id:
            return [c for c in self._cost_log if c["agent_id"] == agent_id]
        return list(self._cost_log)

    def total_cost(self, agent_id: str | None = None) -> float:
        """Sum of all tracked costs (USD)."""
        return sum(c["cost_usd"] for c in self.get_costs(agent_id))


# ---------------------------------------------------------------------------
# Tool definition helper
# ---------------------------------------------------------------------------


def define_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    """Build a tool definition in Anthropic's schema format.

    Example::

        search_tool = define_tool(
            name="search_codebase",
            description="Search the codebase for relevant code snippets",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "file_pattern": {"type": "string", "description": "Glob pattern"},
            },
            required=["query"],
        )
    """
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": parameters,
            "required": required or [],
        },
    }


# ---------------------------------------------------------------------------
# Multi-turn tool use loop
# ---------------------------------------------------------------------------


def handle_tool_loop(
    client: HolusClaudeClient,
    cached_prompt: CachedPrompt,
    initial_message: str,
    tool_handlers: dict[str, Any],
    *,
    tier: ModelTier = "operational",
    max_turns: int = 10,
    agent_id: str = "unknown",
) -> str:
    """Execute a multi-turn tool-use loop until Claude produces a final text response.

    This is the core agentic loop:  Claude reasons, calls tools, receives
    results, reasons again -- repeating until it emits a final text block.

    Args:
        client: ``HolusClaudeClient`` instance.
        cached_prompt: Cached prompt with tool definitions.
        initial_message: The user's request.
        tool_handlers: Mapping of tool names to handler callables.
        tier: Model tier for routing.
        max_turns: Safety limit on tool-call rounds.
        agent_id: For cost tracking.

    Returns:
        The final text response from Claude.
    """
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": initial_message},
    ]

    for _turn in range(max_turns):
        response = client.call(
            cached_prompt=cached_prompt,
            messages=messages,
            tier=tier,
            agent_id=agent_id,
        )

        if response.stop_reason == "tool_use":
            # Append the assistant's tool-use response
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = tool_handlers.get(block.name)
                    if handler:
                        try:
                            result = handler(**block.input)
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": (
                                        json.dumps(result)
                                        if not isinstance(result, str)
                                        else result
                                    ),
                                }
                            )
                        except Exception as exc:
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"Error: {exc}",
                                    "is_error": True,
                                }
                            )
                    else:
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Unknown tool: {block.name}",
                                "is_error": True,
                            }
                        )

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Extract the final text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
        else:
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            break

    return "Max tool turns reached without final response."
