"""Mem0 integration for hierarchical agent memory.

Three-tier memory hierarchy:
  L1 (Session)  -- current task context, ephemeral.
  L2 (Agent)    -- per-domain patterns, persistent.
  L3 (User)     -- Camilo's preferences and working style, global.

Each agent has its own memory scope (via ``agent_id``).  Agents never
read another agent's memory directly -- the coordinator reads cross-project
patterns from the event bus, not from memory.

Mem0 handles:
  - LLM-powered memory extraction (conversations -> discrete facts)
  - Semantic search over stored memories
  - Deduplication and conflict resolution
  - Temporal decay
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MemoryLevel(StrEnum):
    """Memory hierarchy levels."""

    SESSION = "session"  # L1: ephemeral, current task
    AGENT = "agent"  # L2: persistent, per-domain
    USER = "user"  # L3: global, cross-agent


class HolusMem0Client:
    """Holus wrapper around the Mem0 Python library.

    Can operate in two modes:
      1. **Library mode** (default): Import ``mem0`` directly, use pgvector backend.
      2. **API mode**: Hit a self-hosted Mem0 REST API.

    Usage::

        mem = HolusMem0Client(agent_id="trading-agent")
        mem.add("Asian session breakouts on gold failed 4/5 times", level=MemoryLevel.AGENT)
        results = mem.search("gold breakout patterns", level=MemoryLevel.AGENT)
    """

    USER_ID = "camilo"

    def __init__(
        self,
        agent_id: str = "default-agent",
        api_url: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self._api_url = api_url
        self._config = config
        self._memory = None

    def _get_memory(self):
        """Lazy-init the Mem0 memory client."""
        if self._memory is not None:
            return self._memory

        try:
            from mem0 import Memory

            if self._config:
                self._memory = Memory.from_config(self._config)
            else:
                # Default configuration using pgvector
                default_config = {
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "dbname": "holus_memory",
                            "user": "holus",
                            "password": "holus",
                            "host": "localhost",
                            "port": 5432,
                            "collection_name": "holus_memories",
                            "embedding_model_dims": 1536,
                        },
                    },
                    "llm": {
                        "provider": "anthropic",
                        "config": {
                            "model": "claude-sonnet-4-5-20250514",
                        },
                    },
                }
                self._memory = Memory.from_config(default_config)

        except ImportError:
            logger.warning("mem0 not installed. Memory operations will be no-ops.")
            self._memory = None

        return self._memory

    # -- Add memories --------------------------------------------------------

    def add(
        self,
        content: str,
        *,
        level: MemoryLevel = MemoryLevel.AGENT,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Store a memory fact.

        Args:
            content: The memory text to store.
            level: Memory hierarchy level.
            session_id: Required for L1 (session) memories.
            metadata: Additional metadata tags.
        """
        memory = self._get_memory()
        if memory is None:
            return None

        meta = {"level": level.value, **(metadata or {})}
        if session_id:
            meta["session_id"] = session_id

        try:
            result = memory.add(
                content,
                agent_id=self.agent_id,
                user_id=self.USER_ID,
                metadata=meta,
            )
            logger.debug("Memory added [%s/%s]: %s", self.agent_id, level, content[:80])
            return result
        except Exception:
            logger.exception("Failed to add memory")
            return None

    # -- Search memories -----------------------------------------------------

    def search(
        self,
        query: str,
        *,
        level: MemoryLevel | None = None,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over stored memories.

        Args:
            query: Natural language search query.
            level: Filter to a specific memory level.
            limit: Maximum results to return.
            session_id: Filter to a specific session (L1 only).

        Returns:
            List of memory dicts with ``memory``, ``metadata``, and ``id`` keys.
        """
        memory = self._get_memory()
        if memory is None:
            return []

        try:
            results = memory.search(
                query=query,
                agent_id=self.agent_id,
                user_id=self.USER_ID,
                limit=limit,
            )

            memories = results if isinstance(results, list) else results.get("results", [])

            # Filter by level and session if specified
            if level:
                memories = [
                    m for m in memories if m.get("metadata", {}).get("level") == level.value
                ]

            if session_id:
                memories = [
                    m for m in memories if m.get("metadata", {}).get("session_id") == session_id
                ]

            return memories

        except Exception:
            logger.exception("Failed to search memory")
            return []

    # -- Get all memories ----------------------------------------------------

    def get_all(self, level: MemoryLevel | None = None) -> list[dict[str, Any]]:
        """Retrieve all memories for this agent.  Used by weekly review."""
        memory = self._get_memory()
        if memory is None:
            return []

        try:
            results = memory.get_all(
                agent_id=self.agent_id,
                user_id=self.USER_ID,
            )

            memories = results if isinstance(results, list) else results.get("results", [])

            if level:
                memories = [
                    m for m in memories if m.get("metadata", {}).get("level") == level.value
                ]

            return memories
        except Exception:
            logger.exception("Failed to get all memories")
            return []

    # -- Update a memory -----------------------------------------------------

    def update(self, memory_id: str, content: str) -> dict[str, Any] | None:
        """Update an existing memory (e.g., adding trade outcome)."""
        memory = self._get_memory()
        if memory is None:
            return None

        try:
            return memory.update(memory_id=memory_id, data=content)
        except Exception:
            logger.exception("Failed to update memory %s", memory_id)
            return None

    # -- Delete a memory -----------------------------------------------------

    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        memory = self._get_memory()
        if memory is None:
            return False

        try:
            memory.delete(memory_id=memory_id)
            return True
        except Exception:
            logger.exception("Failed to delete memory %s", memory_id)
            return False

    # -- User-level memories (L3, cross-agent) ------------------------------

    def add_user_preference(self, preference: str) -> dict[str, Any] | None:
        """Store a global preference accessible by all agents (L3)."""
        return self.add(
            preference,
            level=MemoryLevel.USER,
            metadata={"category": "preference"},
        )

    def get_user_context(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve Camilo's global preferences and working style."""
        return self.search(
            "user preferences and working style",
            level=MemoryLevel.USER,
            limit=limit,
        )
