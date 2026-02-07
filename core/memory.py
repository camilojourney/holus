"""
Memory Store — ChromaDB-based persistent memory for agents.
Each agent gets its own collection + access to a shared collection.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.config import Settings
from loguru import logger


class MemoryStore:
    """Persistent vector memory using ChromaDB."""

    def __init__(self, persist_dir: str = "~/.holus/memory"):
        self.persist_dir = os.path.expanduser(persist_dir)
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info(f"Memory store initialized at {self.persist_dir}")

    def get_collection(self, agent_name: str) -> chromadb.Collection:
        """Get or create a collection for a specific agent."""
        return self.client.get_or_create_collection(
            name=f"agent_{agent_name}",
            metadata={"agent": agent_name},
        )

    def get_shared_collection(self) -> chromadb.Collection:
        """Get the shared collection accessible by all agents."""
        return self.client.get_or_create_collection(
            name="shared",
            metadata={"type": "shared"},
        )

    def store(
        self,
        agent_name: str,
        content: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
        shared: bool = False,
    ):
        """Store a memory entry."""
        collection = self.get_shared_collection() if shared else self.get_collection(agent_name)

        if doc_id is None:
            doc_id = f"{agent_name}_{datetime.now().isoformat()}"

        meta = {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )
        logger.debug(f"Stored memory for {agent_name}: {content[:80]}...")

    def recall(
        self,
        agent_name: str,
        query: str,
        n_results: int = 5,
        shared: bool = False,
    ) -> list[dict]:
        """Recall relevant memories by semantic search."""
        collection = self.get_shared_collection() if shared else self.get_collection(agent_name)

        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )

        memories = []
        for i, doc in enumerate(results["documents"][0]):
            memories.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })

        return memories

    def get_recent(self, agent_name: str, limit: int = 10) -> list[dict]:
        """Get most recent memories for an agent."""
        collection = self.get_collection(agent_name)
        if collection.count() == 0:
            return []

        results = collection.get(
            limit=limit,
            include=["documents", "metadatas"],
        )

        memories = []
        for i, doc in enumerate(results["documents"]):
            memories.append({
                "content": doc,
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            })

        # Sort by timestamp descending
        memories.sort(
            key=lambda m: m.get("metadata", {}).get("timestamp", ""),
            reverse=True,
        )
        return memories[:limit]
