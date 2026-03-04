"""Tests for holus.agents.base — BaseAgent lifecycle, hooks, and infrastructure.

Covers:
  - Initialization (config loading, infrastructure clients)
  - Abstract interface enforcement
  - Overridable hooks (system_prompt, tools, model_tier)
  - Cached prompt builder
  - Kill switch checking
  - Event publishing
  - Lazy memory and langfuse loading
  - Graph compilation and run lifecycle
  - Resource cleanup
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.agents.base import BaseAgent
from holus.core.config import AgentConfig, HolusConfig
from holus.core.events import EventType
from holus.core.kill_switch import KillSwitchActive, KillSwitchState
from holus.integrations.claude_api.client import CachedPrompt

# ---------------------------------------------------------------------------
# Concrete subclass for testing
# ---------------------------------------------------------------------------


class StubAgent(BaseAgent):
    """Minimal concrete subclass of BaseAgent for testing."""

    agent_name: str = "stub-agent"

    def build_graph(self):
        graph = MagicMock()
        graph.compile.return_value = MagicMock()
        return graph

    def default_state(self) -> dict[str, Any]:
        return {"step": "init"}


def _make_agent(**overrides: Any) -> StubAgent:
    """Create a StubAgent with mocked infrastructure."""
    config = MagicMock(spec=HolusConfig)
    config.anthropic_api_key = "sk-test-key"
    config.redis_url = "redis://localhost:6379"
    config.mem0_api_url = "http://localhost:8080"
    config.langfuse_public_key = ""
    config.langfuse_secret_key = ""
    config.langfuse_host = "http://localhost:3000"

    agent_config = MagicMock(spec=AgentConfig)
    agent_config.default_model_tier = "operational"
    agent_config.mem0_scope = "stub-agent"

    for k, v in overrides.items():
        if hasattr(config, k):
            setattr(config, k, v)
        if hasattr(agent_config, k):
            setattr(agent_config, k, v)

    with (
        patch("holus.agents.base.redis.Redis.from_url", return_value=MagicMock()),
        patch("holus.agents.base.EventBus", return_value=MagicMock()),
        patch("holus.agents.base.KillSwitch", return_value=MagicMock()),
        patch("holus.agents.base.HolusClaudeClient", return_value=MagicMock()),
    ):
        agent = StubAgent(config=config, agent_config=agent_config)

    return agent


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestInit:
    def test_agent_name_set(self) -> None:
        agent = _make_agent()
        assert agent.agent_name == "stub-agent"

    def test_config_stored(self) -> None:
        agent = _make_agent()
        assert agent.config is not None
        assert agent.agent_config is not None

    def test_infrastructure_clients_created(self) -> None:
        agent = _make_agent()
        assert agent.claude is not None
        assert agent.event_bus is not None
        assert agent.kill_switch is not None

    def test_lazy_clients_not_initialized(self) -> None:
        agent = _make_agent()
        assert agent._langfuse is None
        assert agent._memory is None


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class TestAbstractInterface:
    def test_cannot_instantiate_base_directly(self) -> None:
        with (
            pytest.raises(TypeError, match="abstract method"),
            patch("holus.agents.base.redis.Redis.from_url"),
            patch("holus.agents.base.EventBus"),
            patch("holus.agents.base.KillSwitch"),
            patch("holus.agents.base.HolusClaudeClient"),
        ):
            BaseAgent()  # type: ignore[abstract]

    def test_default_state_returns_dict(self) -> None:
        agent = _make_agent()
        state = agent.default_state()
        assert isinstance(state, dict)
        assert state == {"step": "init"}

    def test_build_graph_returns_mock(self) -> None:
        agent = _make_agent()
        graph = agent.build_graph()
        assert graph is not None


# ---------------------------------------------------------------------------
# Overridable hooks
# ---------------------------------------------------------------------------


class TestHooks:
    def test_system_prompt_default(self) -> None:
        agent = _make_agent()
        assert "stub-agent" in agent.system_prompt

    def test_system_prompt_override(self) -> None:
        class CustomAgent(StubAgent):
            @property
            def system_prompt(self) -> str:
                return "I am a custom agent."

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=MagicMock()),
            patch("holus.agents.base.EventBus", return_value=MagicMock()),
            patch("holus.agents.base.KillSwitch", return_value=MagicMock()),
            patch("holus.agents.base.HolusClaudeClient", return_value=MagicMock()),
        ):
            config = MagicMock(spec=HolusConfig)
            config.anthropic_api_key = "sk-test"
            config.redis_url = "redis://localhost:6379"
            agent_config = MagicMock(spec=AgentConfig)
            agent_config.default_model_tier = "operational"
            agent_config.mem0_scope = "custom"
            agent = CustomAgent(config=config, agent_config=agent_config)

        assert agent.system_prompt == "I am a custom agent."

    def test_tools_default_empty(self) -> None:
        agent = _make_agent()
        assert agent.tools == []

    def test_model_tier_from_config(self) -> None:
        agent = _make_agent(default_model_tier="strategic")
        assert agent.model_tier == "strategic"

    def test_model_tier_operational_default(self) -> None:
        agent = _make_agent(default_model_tier="operational")
        assert agent.model_tier == "operational"

    def test_model_tier_classification(self) -> None:
        agent = _make_agent(default_model_tier="classification")
        assert agent.model_tier == "classification"

    def test_model_tier_fallback_for_unknown(self) -> None:
        agent = _make_agent(default_model_tier="unknown_tier")
        assert agent.model_tier == "operational"


# ---------------------------------------------------------------------------
# Cached prompt builder
# ---------------------------------------------------------------------------


class TestCachedPrompt:
    def test_returns_cached_prompt(self) -> None:
        agent = _make_agent()
        cp = agent.cached_prompt()
        assert isinstance(cp, CachedPrompt)

    def test_system_prompt_included(self) -> None:
        agent = _make_agent()
        cp = agent.cached_prompt()
        assert "stub-agent" in cp.system_prompt

    def test_persistent_context_included(self) -> None:
        agent = _make_agent()
        cp = agent.cached_prompt(persistent_context="extra context")
        assert cp.persistent_context == "extra context"


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------


class TestKillSwitch:
    def test_check_does_not_raise_when_inactive(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = False
        agent.check_kill_switch()  # should not raise

    def test_check_raises_when_active(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = True
        agent.kill_switch.get_state.return_value = KillSwitchState(
            activated_at="2026-03-01T00:00:00Z",
            reason="test halt",
            scope="stub-agent",
        )
        with pytest.raises(KillSwitchActive):
            agent.check_kill_switch()

    def test_check_falls_back_to_global_state(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = True
        # First call returns None (agent-specific), second returns global
        agent.kill_switch.get_state.side_effect = [
            None,
            KillSwitchState(
                activated_at="2026-03-01T00:00:00Z",
                reason="global halt",
                scope="global",
            ),
        ]
        with pytest.raises(KillSwitchActive):
            agent.check_kill_switch()


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


class TestEventPublishing:
    def test_publish_event_calls_bus(self) -> None:
        agent = _make_agent()
        agent.publish_event(
            channel="test-channel",
            event_type=EventType.CONTENT_GENERATED,
            payload={"content_id": "abc"},
        )
        agent.event_bus.publish.assert_called_once()

    def test_publish_event_sets_source_agent(self) -> None:
        agent = _make_agent()
        agent.publish_event(
            channel="ch",
            event_type=EventType.CONTENT_GENERATED,
            payload={},
        )
        call_args = agent.event_bus.publish.call_args
        event = call_args[0][1]
        assert event.source_agent == "stub-agent"

    def test_publish_event_with_correlation_id(self) -> None:
        agent = _make_agent()
        agent.publish_event(
            channel="ch",
            event_type=EventType.CONTENT_GENERATED,
            payload={},
            correlation_id="corr-123",
        )
        call_args = agent.event_bus.publish.call_args
        event = call_args[0][1]
        assert event.correlation_id == "corr-123"


# ---------------------------------------------------------------------------
# Graph compilation and run
# ---------------------------------------------------------------------------


class TestCompileAndRun:
    def test_compile_returns_compiled_graph(self) -> None:
        agent = _make_agent()
        compiled = agent.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_run_invokes_graph(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = False

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"step": "done"})

        with patch.object(agent, "compile", return_value=mock_compiled):
            result = await agent.run()

        assert result == {"step": "done"}
        mock_compiled.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_uses_default_state(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = False

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"step": "done"})

        with patch.object(agent, "compile", return_value=mock_compiled):
            await agent.run()

        call_args = mock_compiled.ainvoke.call_args
        assert call_args[0][0] == {"step": "init"}

    @pytest.mark.asyncio
    async def test_run_uses_custom_state(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = False

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"step": "custom"})

        with patch.object(agent, "compile", return_value=mock_compiled):
            await agent.run(state={"step": "custom"})

        call_args = mock_compiled.ainvoke.call_args
        assert call_args[0][0] == {"step": "custom"}

    @pytest.mark.asyncio
    async def test_run_sets_thread_id(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = False

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={})

        with patch.object(agent, "compile", return_value=mock_compiled):
            await agent.run(thread_id="thread-42")

        call_args = mock_compiled.ainvoke.call_args
        config = call_args[1]["config"]
        assert config["configurable"]["thread_id"] == "thread-42"

    @pytest.mark.asyncio
    async def test_run_checks_kill_switch_first(self) -> None:
        agent = _make_agent()
        agent.kill_switch.is_active.return_value = True
        agent.kill_switch.get_state.return_value = KillSwitchState(
            activated_at="2026-03-01T00:00:00Z",
            reason="blocked",
            scope="stub-agent",
        )
        with pytest.raises(KillSwitchActive):
            await agent.run()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_close_closes_event_bus(self) -> None:
        agent = _make_agent()
        agent.close()
        agent.event_bus.close.assert_called_once()

    def test_close_flushes_langfuse_when_initialized(self) -> None:
        agent = _make_agent()
        mock_langfuse = MagicMock()
        agent._langfuse = mock_langfuse
        agent.close()
        mock_langfuse.flush.assert_called_once()

    def test_close_skips_langfuse_when_not_initialized(self) -> None:
        agent = _make_agent()
        assert agent._langfuse is None
        agent.close()  # should not raise
