"""Abstract base class for all Holus agents.

Every domain agent (marketing, pilaster, coordinator)
inherits from ``BaseAgent`` which provides:

  - Configuration loading
  - LangGraph StateGraph scaffolding
  - Mem0 memory integration
  - Langfuse tracing
  - Kill switch checking before every action
  - Redis event bus publishing
  - Structured logging
"""

from __future__ import annotations

import abc
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import redis

from holus.core.config import AgentConfig, HolusConfig
from holus.core.events import EventBus, EventType, HolusEvent
from holus.core.kill_switch import KillSwitch, KillSwitchActive
from holus.integrations.claude_api.client import CachedPrompt, HolusClaudeClient, ModelTier

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)

StateT = TypeVar("StateT")


class BaseAgent(abc.ABC):
    """Abstract base for every Holus agent.

    Subclasses must implement:
      - ``build_graph`` -- return the LangGraph ``StateGraph``.
      - ``default_state``  -- return the initial state dict.

    Optionally override:
      - ``system_prompt`` -- agent-specific system prompt text.
      - ``tools``          -- list of tool definitions.
    """

    agent_name: str = "base-agent"

    def __init__(
        self,
        config: HolusConfig | None = None,
        agent_config: AgentConfig | None = None,
    ) -> None:
        self.config = config or HolusConfig.load(agent_name=self.agent_name)
        self.agent_config = agent_config or self.config.get_agent_config(self.agent_name)

        # -- Infrastructure clients ------------------------------------------
        self.claude = HolusClaudeClient(
            api_key=self.config.anthropic_api_key or None,
            base_url=self.config.anthropic_base_url or None,
            model_map={
                "strategic": self.config.opus_model,
                "operational": self.config.sonnet_model,
                "classification": self.config.haiku_model,
            },
        )

        self._redis = redis.Redis.from_url(self.config.redis_url, decode_responses=True)
        self.event_bus = EventBus(redis_url=self.config.redis_url)
        self.kill_switch = KillSwitch(self._redis)

        # -- Langfuse (lazy) -------------------------------------------------
        self._langfuse = None

        # -- Mem0 (lazy) -----------------------------------------------------
        self._memory = None

        logger.info("Agent %s initialized", self.agent_name)

    # -- Abstract interface --------------------------------------------------

    @abc.abstractmethod
    def build_graph(self) -> StateGraph:
        """Construct and return the LangGraph ``StateGraph`` for this agent."""
        ...

    @abc.abstractmethod
    def default_state(self) -> dict[str, Any]:
        """Return the initial state dict for the graph."""
        ...

    # -- Overridable hooks ---------------------------------------------------

    @property
    def system_prompt(self) -> str:
        """Return the agent's system prompt. Checks PromptLoader first, falls back to default."""
        try:
            loaded = self.prompt_loader.get_prompt(self.agent_name)
            if loaded:
                return loaded
        except Exception:
            pass
        return f"You are the {self.agent_name} agent for Holus."

    def _evaluate_self(self, final_state: dict[str, Any]) -> dict[str, Any] | None:
        """Post-execution self-evaluation via JudgeAgent + trajectory logging.

        Calls JudgeAgent.evaluate_with_routing() on the agent's output,
        then logs the result to trajectory.jsonl. This is THE foundation
        for the self-improvement loop — without judge scores in trajectory,
        no downstream optimization can activate.

        Override in subclasses to customize task/output extraction from state.
        """
        # Extract output from state — subclasses can override for richer extraction
        output = self._extract_output_for_evaluation(final_state)
        if not output:
            return None

        task_summary = final_state.get("task_summary", f"{self.agent_name} run")
        content_type = final_state.get("content_type", "default")

        try:
            from holus.self_improvement.judge import JudgeAgent

            judge = JudgeAgent(api_key=self.config.anthropic_api_key or None)
            evaluation = judge.evaluate_with_routing(
                task=task_summary,
                content_type=content_type,
                output=output[:4000],  # Cap to avoid token waste on long outputs
            )

            # Log to trajectory
            self._log_trajectory(
                task_type=content_type,
                task_summary=task_summary,
                status="success",
                judge_verdict=evaluation.verdict.value,
                judge_score=evaluation.score,
                judge_feedback=evaluation.feedback,
                metadata=final_state.get("metadata", {}),
            )

            return evaluation.to_dict()

        except Exception as exc:
            logger.warning("Self-evaluation failed (non-blocking): %s", exc)
            # Still log the run, just without judge data
            self._log_trajectory(
                task_type=content_type,
                task_summary=task_summary,
                status="success",
                metadata={"evaluation_error": str(exc)},
            )
            return None

    def _extract_output_for_evaluation(self, final_state: dict[str, Any]) -> str | None:
        """Extract the evaluable output from final state. Override in subclasses."""
        # Try common state keys
        for key in ("output", "generated_text", "text", "content", "result"):
            val = final_state.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return None

    def _log_trajectory(
        self,
        *,
        task_type: str = "",
        task_summary: str = "",
        status: str = "success",
        judge_verdict: str | None = None,
        judge_score: float | None = None,
        judge_feedback: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an entry to trajectory.jsonl."""
        try:
            from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

            tl = TrajectoryLogger(
                Path(".self-improvement/memory/trajectory.jsonl")
            )
            entry = TrajectoryEntry(
                agent_id=self.agent_name,
                task_type=task_type,
                task_summary=task_summary,
                status=status,
                judge_verdict=judge_verdict,
                judge_score=judge_score,
                judge_feedback=judge_feedback,
                model_used=self.model_tier,
                metadata={
                    "schema_version": 2,
                    "prompt_variant_id": self._get_prompt_variant_id(),
                    **(metadata or {}),
                },
            )
            tl.append(entry)
        except Exception as exc:
            logger.warning("Trajectory logging failed (non-blocking): %s", exc)

    def _get_prompt_variant_id(self) -> str:
        """Return the current prompt variant ID for observability."""
        try:
            from pathlib import Path as _Path

            variant_path = _Path("config/prompts") / self.agent_name / "current.md"
            if variant_path.exists():
                return f"layer1:{variant_path.name}"
            return "layer2:canonical"
        except Exception:
            return "unknown"

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Return tool definitions.  Override in subclasses."""
        return []

    @property
    def model_tier(self) -> ModelTier:
        """Default model tier for this agent."""
        tier = self.agent_config.default_model_tier
        # Narrow the type for the client
        if tier in ("strategic", "operational", "classification"):
            return tier  # type: ignore[return-value]
        return "operational"

    # -- Cached prompt builder -----------------------------------------------

    def cached_prompt(self, persistent_context: str = "") -> CachedPrompt:
        """Build a ``CachedPrompt`` from the agent's system prompt and tools."""
        return CachedPrompt(
            system_prompt=self.system_prompt,
            tools=self.tools,
            persistent_context=persistent_context,
        )

    # -- Lifecycle -----------------------------------------------------------

    def check_kill_switch(self) -> None:
        """Raise ``KillSwitchActive`` if this agent should halt."""
        if self.kill_switch.is_active(self.agent_name):
            state = self.kill_switch.get_state(self.agent_name) or self.kill_switch.get_state(
                "global"
            )
            if state:
                raise KillSwitchActive(self.agent_name, state)

    def publish_event(
        self,
        channel: str,
        event_type: EventType,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        """Publish a domain event to the Redis event bus."""
        event = HolusEvent(
            source_agent=self.agent_name,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        self.event_bus.publish(channel, event)

    # -- Memory integration (Mem0) ------------------------------------------

    @property
    def memory(self):
        """Lazy-loaded Mem0 memory client."""
        if self._memory is None:
            from holus.memory.mem0_client import HolusMem0Client

            self._memory = HolusMem0Client(
                api_url=self.config.mem0_api_url,
                agent_id=self.agent_config.mem0_scope,
            )
        return self._memory

    # -- Prompt loading (lazy) ----------------------------------------------

    @property
    def prompt_loader(self):
        """Lazy-loaded PromptLoader instance."""
        if not hasattr(self, "_prompt_loader") or self._prompt_loader is None:
            from holus.core.prompt_loader import PromptLoader

            self._prompt_loader = PromptLoader()
        return self._prompt_loader

    # -- Observability (Langfuse) -------------------------------------------

    @property
    def langfuse(self):
        """Lazy-loaded Langfuse client."""
        if self._langfuse is None:
            from holus.observability.langfuse_client import create_langfuse_client

            self._langfuse = create_langfuse_client(
                public_key=self.config.langfuse_public_key or None,
                secret_key=self.config.langfuse_secret_key or None,
                host=self.config.langfuse_host,
            )
        return self._langfuse

    # -- Graph compilation ---------------------------------------------------

    def compile(self, checkpointer=None):
        """Compile the LangGraph ``StateGraph`` with optional checkpointing."""
        graph = self.build_graph()
        return graph.compile(checkpointer=checkpointer)

    async def run(
        self,
        state: dict[str, Any] | None = None,
        *,
        thread_id: str | None = None,
        checkpointer=None,
    ) -> dict[str, Any]:
        """Build, compile, and execute the agent graph.

        Returns the final state dict.
        """
        self.check_kill_switch()

        app = self.compile(checkpointer=checkpointer)
        initial = state or self.default_state()

        config: dict[str, Any] = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}

        # Langfuse tracing (optional — does not block execution)
        trace = None
        try:
            if self._langfuse is not None or (
                self.config.langfuse_public_key and self.config.langfuse_secret_key
            ):
                trace = self.langfuse.trace(
                    name=f"{self.agent_name}/run",
                    metadata={"agent_name": self.agent_name, "model_tier": self.model_tier},
                    tags=[self.agent_name, self.model_tier],
                )
        except Exception:
            logger.debug("Langfuse tracing unavailable; continuing without trace")

        final_state = await app.ainvoke(initial, config=config)

        # Post-execution self-evaluation hook
        self_eval = self._evaluate_self(final_state)
        if self_eval is not None:
            final_state["_self_evaluation"] = self_eval

        # Flush Langfuse if trace was created
        if trace is not None:
            try:
                self.langfuse.flush()
            except Exception:
                logger.debug("Langfuse flush failed; non-critical")

        return final_state

    # -- Cleanup -------------------------------------------------------------

    def close(self) -> None:
        """Release resources."""
        self.event_bus.close()
        if self._langfuse is not None:
            self._langfuse.flush()
