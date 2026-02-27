"""Shared pytest fixtures for Holus test suite."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

# --- Mock Claude Client ---


@pytest.fixture
def mock_claude_response():
    """Factory for mock Claude API responses."""

    def _make(text: str = "Mock response", tool_calls: list | None = None):
        response = MagicMock()
        response.stop_reason = "end_turn" if not tool_calls else "tool_use"

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text

        response.content = [text_block]
        response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=80,
            cache_creation_input_tokens=20,
        )
        return response

    return _make


@pytest.fixture
def mock_claude_client(mock_claude_response):
    """Mock HolusClaudeClient that returns configurable responses."""
    client = MagicMock()
    client.call.return_value = mock_claude_response()
    client._cost_log = []
    client.get_costs.return_value = []
    return client


# --- Mock Redis ---


@pytest.fixture
def mock_redis():
    """Mock Redis client for event bus and kill switch tests."""
    redis = MagicMock()
    redis.publish = MagicMock(return_value=1)
    redis.xadd = MagicMock(return_value="1234567890-0")
    redis.xrange = MagicMock(return_value=[])
    redis.xread = MagicMock(return_value=[])
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock(return_value=True)
    redis.delete = MagicMock(return_value=1)
    redis.pubsub = MagicMock(return_value=MagicMock())
    return redis


# --- Mock Mem0 ---


@pytest.fixture
def mock_mem0():
    """Mock Mem0 client for memory tests."""
    mem0 = MagicMock()
    mem0.add.return_value = {"id": "mem_001"}
    mem0.search.return_value = {"results": []}
    mem0.get_all.return_value = {"results": []}
    mem0.update.return_value = {"id": "mem_001"}
    mem0.delete.return_value = True
    return mem0


# --- Sample Data Fixtures ---


@pytest.fixture
def sample_trade_signal() -> dict[str, Any]:
    """Sample trade signal for trading agent tests."""
    return {
        "ticker": "AAPL",
        "direction": "long",
        "confidence": 0.85,
        "entry_price": 195.50,
        "stop_loss": 192.00,
        "take_profit": 202.00,
        "reasoning": "Strong momentum with volume confirmation above 20-day average.",
        "timeframe": "1d",
    }


@pytest.fixture
def sample_risk_assessment() -> dict[str, Any]:
    """Sample risk assessment for trading agent tests."""
    return {
        "approved": True,
        "position_size": 50,
        "stop_loss": 192.00,
        "take_profit": 202.00,
        "risk_score": 0.35,
        "max_loss_usd": 175.00,
        "rejection_reason": None,
    }


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Sample Holus configuration for config tests."""
    return {
        "ANTHROPIC_API_KEY": "sk-ant-test-key-not-real",
        "REDIS_URL": "redis://localhost:6379",
        "DATABASE_URL": "postgresql://holus:holus@localhost:5432/holus",
        "LANGFUSE_HOST": "http://localhost:3001",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "HOLUS_ENV": "test",
        "HOLUS_LOG_LEVEL": "DEBUG",
    }


@pytest.fixture
def tmp_trajectory(tmp_path):
    """Temporary trajectory directory for testing."""
    trajectory_dir = tmp_path / "trajectory"
    trajectory_dir.mkdir()
    return trajectory_dir
