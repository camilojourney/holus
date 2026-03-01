"""Integration tests for Holus.

Covers:
  1. MarketingAgent full cycle (observe → reason → act → evaluate) with mocked LLM.
  2. content_queue round-trip (enqueue / approve / reject / mark_published).
  3. MCP server tool dispatch (skipped — no MCP dispatcher module found in integrations/).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
import yaml

from holus.agents.marketing.content_queue import (
    QueuedContent,
    approve,
    enqueue,
    list_approved,
    list_pending,
    mark_published,
    reject,
)
from holus.core.config import HolusConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_holus_config(tmp_path: Path) -> HolusConfig:
    """Build a minimal HolusConfig that won't try to connect to Redis/Claude."""
    return HolusConfig(
        ANTHROPIC_API_KEY="",  # empty → triggers fallback path (no real API calls)
        REDIS_URL="redis://localhost:6379",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
    )


def _make_fake_products(tmp_path: Path) -> None:
    """Write a minimal config/products.yaml under tmp_path."""
    products_dir = tmp_path / "config"
    products_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "products": {
            "pilaster": {
                "name": "Pilaster",
                "tagline": "AI image studio",
                "description": "Generate and edit images with AI.",
                "platforms": ["linkedin", "twitter"],
                "audience": "Designers",
                "pain_point": "Slow image iteration",
            }
        }
    }
    (products_dir / "products.yaml").write_text(yaml.dump(data))


def _make_fake_knowledge(tmp_path: Path) -> None:
    """Write placeholder knowledge files under tmp_path."""
    knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "platforms.md").write_text("Use concise, value-first content.")
    (knowledge_dir / "audience-profiles.md").write_text("Audience: tech professionals.")


def _make_fake_memory(tmp_path: Path) -> None:
    """Write a minimal MEMORY.md under tmp_path."""
    memory_dir = tmp_path / ".self-improvement"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "MEMORY.md").write_text("## Holus Memory\n\nNo entries yet.\n")


def _make_mock_redis() -> MagicMock:
    redis = MagicMock()
    redis.get.return_value = None  # kill switch not set
    redis.publish.return_value = 1
    redis.xadd.return_value = "1234567890-0"
    redis.xrange.return_value = []
    redis.xread.return_value = []
    redis.set.return_value = True
    redis.delete.return_value = 1
    redis.pubsub.return_value = MagicMock()
    return redis


# ---------------------------------------------------------------------------
# 1. MarketingAgent full cycle
# ---------------------------------------------------------------------------


class TestMarketingAgentCycle:
    """End-to-end test for the MarketingAgent observe→reason→act→evaluate loop."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path):
        """Prepare filesystem fixtures and patch infrastructure."""
        self.tmp = tmp_path

        # Create required files relative to tmp_path
        _make_fake_products(tmp_path)
        _make_fake_knowledge(tmp_path)
        _make_fake_memory(tmp_path)
        (tmp_path / "data" / "content-queue").mkdir(parents=True, exist_ok=True)

        # Patch cwd so relative Path() lookups in MarketingAgent resolve to tmp_path
        with patch("holus.agents.marketing.agent.Path") as _:
            pass  # We'll patch at a higher level below

    def test_full_cycle_with_mocked_llm(self, tmp_path: Path, monkeypatch):
        """
        Run MarketingAgent.run() with:
          - No Anthropic API key (forces fallback path so no real HTTP calls)
          - Mocked Redis (no real Redis needed)
          - Filesystem rooted at tmp_path via monkeypatching class-level Path constants

        Asserts all 4 stages completed and state is populated.
        """
        from holus.agents.marketing.agent import MarketingAgent

        # -- Patch path constants to point to tmp_path ---------------------
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._PRODUCTS_PATH",
            tmp_path / "config" / "products.yaml",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._KNOWLEDGE_DIR",
            tmp_path / ".self-improvement" / "knowledge" / "current",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._MEMORY_PATH",
            tmp_path / ".self-improvement" / "MEMORY.md",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._QUEUE_DIR",
            tmp_path / "data" / "content-queue",
        )
        traj_dir = tmp_path / ".self-improvement" / "memory"
        traj_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._TRAJECTORY_PATH",
            traj_dir / "trajectory.jsonl",
        )

        mock_redis = _make_mock_redis()

        # -- Patch Redis and EventBus so no real connections are attempted --
        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_event_bus_cls,
        ):
            mock_event_bus_cls.return_value = MagicMock()

            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)

            # Run the full cycle (no API key → fallback decisions + fallback content)
            final_state = asyncio.run(agent.run())

        # -- Assertions -------------------------------------------------------
        # observe: product_updates loaded
        assert isinstance(final_state.get("product_updates"), dict)
        assert "products" in final_state["product_updates"]

        # reason: content_decisions produced (fallback path)
        decisions = final_state.get("content_decisions", [])
        assert isinstance(decisions, list)
        assert len(decisions) >= 1, "Expected at least one content decision"

        # act: generated_content produced
        generated = final_state.get("generated_content", [])
        assert isinstance(generated, list)
        assert len(generated) >= 1, "Expected at least one generated content piece"

        first = generated[0]
        assert "text" in first
        assert len(first["text"]) > 0

        # evaluate: evaluation dict present
        evaluation = final_state.get("evaluation", {})
        assert isinstance(evaluation, dict)
        assert "cycle_id" in evaluation or "decisions_count" in evaluation or len(evaluation) > 0

        # No error
        assert final_state.get("error") is None

    def test_observe_loads_products_and_knowledge(self, tmp_path: Path, monkeypatch):
        """Observe phase should load products.yaml and knowledge files."""
        from holus.agents.marketing.agent import MarketingAgent

        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._PRODUCTS_PATH",
            tmp_path / "config" / "products.yaml",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._KNOWLEDGE_DIR",
            tmp_path / ".self-improvement" / "knowledge" / "current",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._MEMORY_PATH",
            tmp_path / ".self-improvement" / "MEMORY.md",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._QUEUE_DIR",
            tmp_path / "data" / "content-queue",
        )

        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_event_bus_cls,
        ):
            mock_event_bus_cls.return_value = MagicMock()
            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)

            initial_state: dict[str, Any] = agent.default_state()
            result = asyncio.run(agent.observe(initial_state))  # type: ignore[arg-type]

        assert "products" in result.get("product_updates", {})
        assert isinstance(result.get("knowledge"), dict)
        assert "platforms" in result["knowledge"]
        assert "No entries yet" in result.get("memory_context", "")


# ---------------------------------------------------------------------------
# 2. content_queue round-trip
# ---------------------------------------------------------------------------


class TestContentQueueRoundTrip:
    """Tests for the content_queue enqueue/approve/reject/mark_published flow."""

    def _make_item(self, **kwargs) -> QueuedContent:
        defaults = {
            "product": "pilaster",
            "platform": "linkedin",
            "content_type": "tutorial",
            "topic": "Test topic",
            "text": "This is a test post about Pilaster.",
            "reasoning": "Integration test fixture",
        }
        defaults.update(kwargs)
        return QueuedContent(**defaults)

    def test_enqueue_and_list_pending(self, tmp_path: Path, monkeypatch):
        """enqueue → list_pending returns the item."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        path = enqueue(item)

        assert path.exists()
        assert path.suffix == ".yaml"

        pending = list_pending()
        assert len(pending) == 1
        assert pending[0].piece_id == item.piece_id
        assert pending[0].status == "pending_review"

    def test_approve_moves_to_approved(self, tmp_path: Path, monkeypatch):
        """enqueue → approve → list_approved returns the item."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)

        approve(item.piece_id)

        pending = list_pending()
        assert len(pending) == 0

        approved = list_approved()
        assert len(approved) == 1
        assert approved[0].piece_id == item.piece_id
        assert approved[0].status == "approved"

    def test_reject_with_reason(self, tmp_path: Path, monkeypatch):
        """enqueue → reject → item status is 'rejected' with reason."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)

        reject(item.piece_id, reason="Not relevant this week")

        pending = list_pending()
        assert len(pending) == 0

        # Read directly from file to verify rejection_reason
        queue_file = tmp_path / "queue" / f"{item.piece_id}.yaml"
        data = yaml.safe_load(queue_file.read_text())
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Not relevant this week"

    def test_mark_published(self, tmp_path: Path, monkeypatch):
        """enqueue → approve → mark_published → status is 'published'."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)
        approve(item.piece_id)
        mark_published(item.piece_id, post_id="post_001")

        queue_file = tmp_path / "queue" / f"{item.piece_id}.yaml"
        data = yaml.safe_load(queue_file.read_text())
        assert data["status"] == "published"

    def test_multiple_items_in_queue(self, tmp_path: Path, monkeypatch):
        """Multiple items can be enqueued and listed."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        items = [self._make_item(topic=f"Topic {i}") for i in range(3)]
        for item in items:
            enqueue(item)

        pending = list_pending()
        assert len(pending) == 3

        # Approve one, reject another
        approve(items[0].piece_id)
        reject(items[1].piece_id, reason="Off-brand")

        pending = list_pending()
        assert len(pending) == 1
        assert pending[0].piece_id == items[2].piece_id

        approved = list_approved()
        assert len(approved) == 1
        assert approved[0].piece_id == items[0].piece_id


# ---------------------------------------------------------------------------
# 3. MCP server tool dispatch
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "No MCP dispatcher module found in src/holus/integrations/. "
        "Holus calls external MCP servers (genpeli-mcp, social-media-mcp, pilaster-mcp) "
        "via HTTP but does not host an MCP server itself. "
        "MCP integration tests should be added when holus/integrations/mcp/ exists."
    )
)
def test_mcp_tool_dispatch_placeholder():
    """Placeholder for MCP tool dispatch tests."""
    pass
