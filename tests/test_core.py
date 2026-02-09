import asyncio
from unittest.mock import MagicMock

import pytest
from core.base_agent import BaseAgent
from core.llm import LLMProvider
from core.memory import MemoryStore
from core.notifier import Notifier


def _mock_notifier() -> Notifier:
    n = MagicMock(spec=Notifier)
    n.notify = MagicMock(return_value=asyncio.coroutine(lambda *a, **k: None)())
    return n


class TestBaseAgent:
    def test_agent_initialization(self):
        # Mock agent for testing
        class MockAgent(BaseAgent):
            name = "test_agent"
            schedule = "every 1 hour"

            def get_tools(self):
                return []

            def get_system_prompt(self):
                return "Test prompt"

            async def run(self):
                pass

        agent = MockAgent(
            llm_provider=MagicMock(spec=LLMProvider),
            memory=MagicMock(spec=MemoryStore),
            notifier=_mock_notifier(),
            config={"enabled": True},
        )
        assert agent.name == "test_agent"
        assert agent.schedule == "every 1 hour"
        assert agent.status == "idle"
        assert agent._run_count == 0
        assert agent._run_history == []
