"""
Base Agent — The foundation class for all Holus agents.

Each agent has its own tools, memory, system prompt, and scheduled tasks.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from loguru import logger

from core.llm import LLMProvider, TaskComplexity
from core.memory import MemoryStore
from core.notifier import Notifier


@dataclass
class RunRecord:
    """Structured record of a single agent run."""
    run_number: int
    timestamp: str
    status: str  # "completed" | "error"
    result_summary: str
    duration_seconds: float
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all Holus agents.

    Each agent has:
    - A name and description
    - Its own tools
    - A system prompt
    - Access to memory (per-agent + shared)
    - Notification capability
    - A schedule for autonomous execution
    """

    name: str = "base_agent"
    description: str = "A base agent"
    schedule: str = "manual"  # cron-like or "every X hours/minutes"

    def __init__(
        self,
        llm_provider: LLMProvider,
        memory: MemoryStore,
        notifier: Notifier,
        config: dict,
    ):
        self.llm_provider = llm_provider
        self.memory = memory
        self.notifier = notifier
        self.config = config
        self._agent_executor: Optional[AgentExecutor] = None
        self._run_count = 0
        self._last_run: Optional[datetime] = None
        self._is_running = False
        self._last_error: Optional[str] = None
        self._run_history: list[RunRecord] = []

        logger.info(f"Agent '{self.name}' initialized | schedule: {self.schedule}")

    # --- Abstract methods that each agent must implement ---

    @abstractmethod
    def get_tools(self) -> list:
        """Return the list of LangChain tools this agent can use."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt that defines this agent's behavior."""
        ...

    @abstractmethod
    async def run(self) -> dict[str, Any]:
        """
        Execute the agent's main task.
        Called on schedule or manually.
        Returns a dict with results/status.
        """
        ...

    # --- Built-in capabilities ---

    def get_llm(self, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> BaseChatModel:
        """Get the LLM for this agent, respecting per-agent config."""
        agent_provider = self.config.get("llm_provider")
        if agent_provider:
            return self.llm_provider.get(provider=agent_provider)
        return self.llm_provider.get(complexity=complexity)

    def build_agent_executor(self) -> AgentExecutor:
        """Build a LangChain agent executor with this agent's tools and prompt."""
        if self._agent_executor is not None:
            return self._agent_executor

        tools = self.get_tools()
        llm = self.get_llm()

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(llm, tools, prompt)
        self._agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
        )
        return self._agent_executor

    async def execute(self, task: str, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> str:
        """Execute a single task using this agent's tools and LLM."""
        executor = self.build_agent_executor()
        try:
            result = await asyncio.to_thread(
                executor.invoke, {"input": task}
            )
            return result.get("output", str(result))
        except Exception as e:
            logger.error(f"Agent '{self.name}' execution error: {e}")
            return f"Error: {e}"

    async def notify(self, message: str):
        """Send a notification from this agent."""
        await self.notifier.notify(message, agent_name=self.name)

    async def request_approval(self, action: str, details: str) -> bool:
        """Request human approval before taking a high-stakes action."""
        return await self.notifier.request_approval(self.name, action, details)

    def remember(self, content: str, metadata: Optional[dict] = None, shared: bool = False):
        """Store something in this agent's memory."""
        self.memory.store(self.name, content, metadata=metadata, shared=shared)

    def recall(self, query: str, n_results: int = 5, shared: bool = False) -> list[dict]:
        """Recall relevant memories."""
        return self.memory.recall(self.name, query, n_results=n_results, shared=shared)

    async def scheduled_run(self):
        """Wrapper for scheduled execution with logging and error handling."""
        self._run_count += 1
        self._last_run = datetime.now()
        self._is_running = True
        self._last_error = None
        start_time = time.monotonic()
        logger.info(f"🚀 Agent '{self.name}' starting scheduled run #{self._run_count}")

        try:
            result = await self.run()
            duration = time.monotonic() - start_time
            logger.info(f"✅ Agent '{self.name}' completed run #{self._run_count}")

            # Store structured run record
            record = RunRecord(
                run_number=self._run_count,
                timestamp=self._last_run.isoformat(),
                status="completed",
                result_summary=str(result)[:200],
                duration_seconds=round(duration, 2),
            )
            self._run_history.append(record)

            # Also store in ChromaDB memory
            self.remember(
                f"Run #{self._run_count} at {self._last_run.isoformat()}: {str(result)[:500]}",
                metadata={"type": "run_result", "run_number": self._run_count},
            )

            return result
        except Exception as e:
            duration = time.monotonic() - start_time
            self._last_error = str(e)
            logger.error(f"❌ Agent '{self.name}' run #{self._run_count} failed: {e}")

            record = RunRecord(
                run_number=self._run_count,
                timestamp=self._last_run.isoformat(),
                status="error",
                result_summary="",
                duration_seconds=round(duration, 2),
                error=str(e),
            )
            self._run_history.append(record)

            await self.notify(f"⚠️ Run failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self._is_running = False

    @property
    def status(self) -> str:
        """Current execution status: idle, running, or error."""
        if self._is_running:
            return "running"
        if self._last_error is not None:
            return "error"
        return "idle"

    def get_status(self) -> dict:
        """Get current status of this agent."""
        return {
            "name": self.name,
            "description": self.description,
            "schedule": self.schedule,
            "run_count": self._run_count,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "enabled": self.config.get("enabled", True),
            "status": self.status,
        }

    def get_run_history(self, limit: int = 20) -> list[dict]:
        """Get structured run history, newest first."""
        limit = min(max(limit, 1), 100)
        history = list(reversed(self._run_history))
        return [asdict(r) for r in history[:limit]]
