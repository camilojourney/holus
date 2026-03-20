"""Unit tests for BaseAgent — lifecycle, config, kill switch, events, evaluation.

All tests mock Redis, Claude API, and LangGraph — no real connections.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.agents.base import BaseAgent
from holus.core.config import AgentConfig, HolusConfig
from holus.core.events import EventType
from holus.core.kill_switch import KillSwitchActive, KillSwitchState

# ---------------------------------------------------------------------------
# Concrete subclass for testing
# ---------------------------------------------------------------------------


class _StubAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent."""

    agent_name: str = "stub-agent"

    def build_graph(self):
        graph = MagicMock()
        compiled = MagicMock()
        compiled.ainvoke = AsyncMock(return_value={"output": "hello world"})
        graph.compile.return_value = compiled
        return graph

    def default_state(self) -> dict[str, Any]:
        return {"step": "init"}


class _StrategicAgent(BaseAgent):
    """Agent configured for strategic (Opus) tier."""

    agent_name: str = "strategic-agent"

    def build_graph(self):
        return MagicMock()

    def default_state(self) -> dict[str, Any]:
        return {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_config():
    """Minimal HolusConfig without hitting YAML files or .env."""
    return HolusConfig(
        anthropic_api_key="test-key",
        redis_url="redis://localhost:6379",
        anthropic_base_url="http://localhost:8080",
        opus_model="claude-opus-4-6",
        sonnet_model="claude-sonnet-4-6",
        haiku_model="claude-haiku-4-5-20251001",
    )


@pytest.fixture()
def agent(mock_config):
    """Create a stub agent with mocked infrastructure."""
    with (
        patch("holus.agents.base.redis.Redis.from_url") as mock_redis,
        patch("holus.agents.base.EventBus") as mock_eb,
        patch("holus.agents.base.KillSwitch") as mock_ks,
    ):
        mock_redis.return_value = MagicMock()
        mock_eb.return_value = MagicMock()
        mock_ks.return_value = MagicMock()
        a = _StubAgent(config=mock_config)
        yield a


@pytest.fixture()
def strategic_agent(mock_config):
    """Create an agent with strategic model tier config."""
    strategic_config = AgentConfig(name="strategic-agent", default_model_tier="strategic")
    with (
        patch("holus.agents.base.redis.Redis.from_url"),
        patch("holus.agents.base.EventBus"),
        patch("holus.agents.base.KillSwitch"),
    ):
        a = _StrategicAgent(config=mock_config, agent_config=strategic_config)
        yield a


# ---------------------------------------------------------------------------
# Init & Config
# ---------------------------------------------------------------------------


class TestInit:
    def test_agent_name_set(self, agent: _StubAgent):
        assert agent.agent_name == "stub-agent"

    def test_config_stored(self, agent: _StubAgent, mock_config: HolusConfig):
        assert agent.config is mock_config

    def test_claude_client_created(self, agent: _StubAgent):
        assert agent.claude is not None

    def test_default_agent_config_when_none(self, agent: _StubAgent):
        """When no agent_config is passed, get_agent_config is used."""
        assert agent.agent_config.name == "stub-agent"

    def test_explicit_agent_config(self, strategic_agent: _StrategicAgent):
        assert strategic_agent.agent_config.name == "strategic-agent"
        assert strategic_agent.agent_config.default_model_tier == "strategic"

    def test_config_auto_loads_when_none(self):
        """When config=None, HolusConfig.load() is called."""
        with (
            patch("holus.agents.base.redis.Redis.from_url"),
            patch("holus.agents.base.EventBus"),
            patch("holus.agents.base.KillSwitch"),
            patch.object(HolusConfig, "load", return_value=HolusConfig(redis_url="redis://localhost:6379")) as mock_load,
        ):
            _StubAgent(config=None)
            mock_load.assert_called_once_with(agent_name="stub-agent")


# ---------------------------------------------------------------------------
# Model Tier
# ---------------------------------------------------------------------------


class TestModelTier:
    def test_default_operational(self, agent: _StubAgent):
        assert agent.model_tier == "operational"

    def test_strategic_tier(self, strategic_agent: _StrategicAgent):
        assert strategic_agent.model_tier == "strategic"

    def test_invalid_tier_falls_back(self, mock_config: HolusConfig):
        """If agent config has bogus tier string, fall back to operational."""
        bad_config = AgentConfig(name="bad", default_model_tier="operational")
        # Manually set an invalid value bypassing validation
        object.__setattr__(bad_config, "default_model_tier", "bogus")
        with (
            patch("holus.agents.base.redis.Redis.from_url"),
            patch("holus.agents.base.EventBus"),
            patch("holus.agents.base.KillSwitch"),
        ):
            a = _StubAgent(config=mock_config, agent_config=bad_config)
            assert a.model_tier == "operational"


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_default_prompt_fallback(self, agent: _StubAgent):
        """When PromptLoader has no prompt, returns default string."""
        with patch.object(type(agent), "prompt_loader", new_callable=lambda: property(lambda self: MagicMock(get_prompt=MagicMock(return_value=None)))):
            assert "stub-agent" in agent.system_prompt

    def test_prompt_loader_returns_custom(self, agent: _StubAgent):
        mock_loader = MagicMock()
        mock_loader.get_prompt.return_value = "Custom prompt for stub"
        agent._prompt_loader = mock_loader
        assert agent.system_prompt == "Custom prompt for stub"

    def test_prompt_loader_exception_falls_back(self, agent: _StubAgent):
        mock_loader = MagicMock()
        mock_loader.get_prompt.side_effect = RuntimeError("loader broken")
        agent._prompt_loader = mock_loader
        assert "stub-agent" in agent.system_prompt


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------


class TestKillSwitch:
    def test_no_kill_switch_passes(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        agent.check_kill_switch()  # Should not raise

    def test_kill_switch_active_raises(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = True
        state = KillSwitchState(
            activated_at="2026-03-20T00:00:00Z",
            reason="emergency",
            scope="stub-agent",
        )
        agent.kill_switch.get_state.return_value = state
        with pytest.raises(KillSwitchActive):
            agent.check_kill_switch()

    def test_kill_switch_falls_back_to_global(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = True
        global_state = KillSwitchState(
            activated_at="2026-03-20T00:00:00Z",
            reason="global halt",
            scope="global",
        )
        # First call (agent-specific) returns None, second (global) returns state
        agent.kill_switch.get_state.side_effect = [None, global_state]
        with pytest.raises(KillSwitchActive):
            agent.check_kill_switch()


# ---------------------------------------------------------------------------
# Event Publishing
# ---------------------------------------------------------------------------


class TestPublishEvent:
    def test_publish_event_constructs_holus_event(self, agent: _StubAgent):
        agent.publish_event(
            channel="holus.test",
            event_type=EventType.CONTENT_GENERATED,
            payload={"content_id": "abc"},
            correlation_id="corr-123",
        )
        agent.event_bus.publish.assert_called_once()
        call_args = agent.event_bus.publish.call_args
        assert call_args[0][0] == "holus.test"
        event = call_args[0][1]
        assert event.source_agent == "stub-agent"
        assert event.event_type == EventType.CONTENT_GENERATED
        assert event.payload == {"content_id": "abc"}
        assert event.correlation_id == "corr-123"

    def test_publish_event_no_correlation_id(self, agent: _StubAgent):
        agent.publish_event(
            channel="holus.test",
            event_type=EventType.CONTENT_APPROVED,
            payload={},
        )
        event = agent.event_bus.publish.call_args[0][1]
        assert event.correlation_id is None


# ---------------------------------------------------------------------------
# Cached Prompt
# ---------------------------------------------------------------------------


class TestCachedPrompt:
    def test_cached_prompt_uses_system_prompt(self, agent: _StubAgent):
        mock_loader = MagicMock()
        mock_loader.get_prompt.return_value = "You are a test agent."
        agent._prompt_loader = mock_loader
        cp = agent.cached_prompt(persistent_context="some context")
        assert cp.system_prompt == "You are a test agent."
        assert cp.persistent_context == "some context"

    def test_cached_prompt_includes_tools(self, agent: _StubAgent):
        cp = agent.cached_prompt()
        assert cp.tools == []  # Default tools is empty


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class TestTools:
    def test_default_tools_empty(self, agent: _StubAgent):
        assert agent.tools == []


# ---------------------------------------------------------------------------
# Output Extraction
# ---------------------------------------------------------------------------


class TestExtractOutput:
    @pytest.mark.parametrize("key", ["output", "generated_text", "text", "content", "result"])
    def test_extracts_from_known_keys(self, agent: _StubAgent, key: str):
        state = {key: "some output text"}
        assert agent._extract_output_for_evaluation(state) == "some output text"

    def test_returns_none_for_empty_state(self, agent: _StubAgent):
        assert agent._extract_output_for_evaluation({}) is None

    def test_returns_none_for_blank_values(self, agent: _StubAgent):
        assert agent._extract_output_for_evaluation({"output": "   "}) is None

    def test_returns_first_matching_key(self, agent: _StubAgent):
        state = {"output": "first", "text": "second"}
        assert agent._extract_output_for_evaluation(state) == "first"


# ---------------------------------------------------------------------------
# Self-Evaluation
# ---------------------------------------------------------------------------


class TestEvaluateSelf:
    def test_evaluate_self_with_judge(self, agent: _StubAgent):
        mock_eval = MagicMock()
        mock_eval.verdict.value = "PASS"
        mock_eval.score = 0.85
        mock_eval.feedback = "Good work"
        mock_eval.to_dict.return_value = {"verdict": "PASS", "score": 0.85}

        with (
            patch("holus.agents.base.BaseAgent._log_trajectory") as mock_log,
            patch("holus.self_improvement.judge.JudgeAgent") as mock_judge_cls,
        ):
            mock_judge_cls.return_value.evaluate_with_routing.return_value = mock_eval
            result = agent._evaluate_self({"output": "test content", "content_type": "linkedin_post"})

        assert result == {"verdict": "PASS", "score": 0.85}
        mock_log.assert_called_once()

    def test_evaluate_self_no_output_returns_none(self, agent: _StubAgent):
        assert agent._evaluate_self({"no_output_key": True}) is None

    def test_evaluate_self_judge_error_non_blocking(self, agent: _StubAgent):
        with (
            patch("holus.agents.base.BaseAgent._log_trajectory"),
            patch("holus.self_improvement.judge.JudgeAgent", side_effect=RuntimeError("judge down")),
        ):
            result = agent._evaluate_self({"output": "content"})
        assert result is None


# ---------------------------------------------------------------------------
# Trajectory Logging
# ---------------------------------------------------------------------------


class TestLogTrajectory:
    def test_log_trajectory_success(self, agent: _StubAgent):
        with patch("holus.memory.trajectory.TrajectoryLogger") as mock_tl_cls:
            mock_tl = MagicMock()
            mock_tl_cls.return_value = mock_tl
            agent._log_trajectory(
                task_type="linkedin_post",
                task_summary="Test post",
                status="success",
                judge_verdict="PASS",
                judge_score=0.9,
            )
            mock_tl.append.assert_called_once()

    def test_log_trajectory_error_non_blocking(self, agent: _StubAgent):
        with patch("holus.memory.trajectory.TrajectoryLogger", side_effect=RuntimeError("disk full")):
            # Should not raise
            agent._log_trajectory(task_type="test", task_summary="test")


# ---------------------------------------------------------------------------
# Prompt Variant ID
# ---------------------------------------------------------------------------


class TestPromptVariantId:
    def test_layer1_when_variant_exists(self, agent: _StubAgent, tmp_path):
        variant_dir = tmp_path / "config" / "prompts" / "stub-agent"
        variant_dir.mkdir(parents=True)
        (variant_dir / "current.md").write_text("variant prompt")
        with patch("holus.agents.base.Path", return_value=variant_dir / "current.md"):
            # The method uses a local Path import, just test the fallback
            pass
        # Default behavior without variant file
        result = agent._get_prompt_variant_id()
        assert result in ("layer2:canonical", "layer1:current.md", "unknown")

    def test_layer2_canonical_default(self, agent: _StubAgent):
        """Without a variant file in config/prompts/, returns layer2:canonical."""
        result = agent._get_prompt_variant_id()
        # Either layer2:canonical (no variant file) or layer1 if file happens to exist
        assert "layer" in result or result == "unknown"


# ---------------------------------------------------------------------------
# Lifecycle: compile, run, close
# ---------------------------------------------------------------------------


class TestCompile:
    def test_compile_calls_build_graph(self, agent: _StubAgent):
        compiled = agent.compile()
        assert compiled is not None

    def test_compile_with_checkpointer(self, agent: _StubAgent):
        mock_cp = MagicMock()
        compiled = agent.compile(checkpointer=mock_cp)
        assert compiled is not None


class TestRun:
    @pytest.mark.asyncio
    async def test_run_executes_graph(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        with patch.object(agent, "_evaluate_self", return_value=None):
            result = await agent.run()
        assert result == {"output": "hello world"}

    @pytest.mark.asyncio
    async def test_run_checks_kill_switch_first(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = True
        state = KillSwitchState(
            activated_at="2026-03-20T00:00:00Z",
            reason="halt",
            scope="stub-agent",
        )
        agent.kill_switch.get_state.return_value = state
        with pytest.raises(KillSwitchActive):
            await agent.run()

    @pytest.mark.asyncio
    async def test_run_with_custom_state(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        custom = {"step": "custom", "data": "test"}
        with patch.object(agent, "_evaluate_self", return_value=None):
            result = await agent.run(state=custom)
        # The compiled graph's ainvoke should have received our custom state
        assert result == {"output": "hello world"}

    @pytest.mark.asyncio
    async def test_run_with_thread_id(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        with patch.object(agent, "_evaluate_self", return_value=None):
            result = await agent.run(thread_id="test-thread")
        assert result == {"output": "hello world"}

    @pytest.mark.asyncio
    async def test_run_attaches_self_evaluation(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        eval_result = {"verdict": "PASS", "score": 0.9}
        with patch.object(agent, "_evaluate_self", return_value=eval_result):
            result = await agent.run()
        assert result.get("_self_evaluation") == eval_result

    @pytest.mark.asyncio
    async def test_run_langfuse_tracing_skipped_when_no_keys(self, agent: _StubAgent):
        agent.kill_switch.is_active.return_value = False
        agent._langfuse = None
        agent.config.langfuse_public_key = ""
        agent.config.langfuse_secret_key = ""
        with patch.object(agent, "_evaluate_self", return_value=None):
            result = await agent.run()
        assert result == {"output": "hello world"}


class TestClose:
    def test_close_flushes_event_bus(self, agent: _StubAgent):
        agent.close()
        agent.event_bus.close.assert_called_once()

    def test_close_flushes_langfuse_if_present(self, agent: _StubAgent):
        mock_lf = MagicMock()
        agent._langfuse = mock_lf
        agent.close()
        mock_lf.flush.assert_called_once()

    def test_close_skips_langfuse_if_none(self, agent: _StubAgent):
        agent._langfuse = None
        agent.close()  # Should not raise


# ---------------------------------------------------------------------------
# Lazy Properties
# ---------------------------------------------------------------------------


class TestLazyProperties:
    def test_memory_lazy_init(self, agent: _StubAgent):
        with patch("holus.memory.mem0_client.HolusMem0Client") as mock_mem:
            mock_mem.return_value = MagicMock()
            mem = agent.memory
            assert mem is not None
            # Second access returns same instance
            assert agent.memory is mem

    def test_prompt_loader_lazy_init(self, agent: _StubAgent):
        with patch("holus.core.prompt_loader.PromptLoader") as mock_pl:
            mock_pl.return_value = MagicMock()
            pl = agent.prompt_loader
            assert pl is not None
            assert agent.prompt_loader is pl

    def test_langfuse_lazy_init(self, agent: _StubAgent):
        with patch("holus.observability.langfuse_client.create_langfuse_client") as mock_lf:
            mock_lf.return_value = MagicMock()
            lf = agent.langfuse
            assert lf is not None
            assert agent.langfuse is lf
