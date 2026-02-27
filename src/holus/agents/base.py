"""Abstract base class for all Holus agents.

Every domain agent (trading, content, coding, pilaster, coordinator)
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
        self.claude = HolusClaudeClient(api_key=self.config.anthropic_api_key or None)

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
        """Return the agent's system prompt.  Override in subclasses."""
        return f"You are the {self.agent_name} agent for Holus."

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

        final_state = await app.ainvoke(initial, config=config)
        return final_state

    # -- Cleanup -------------------------------------------------------------

    def close(self) -> None:
        """Release resources."""
        self.event_bus.close()
        if self._langfuse is not None:
            self._langfuse.flush()
