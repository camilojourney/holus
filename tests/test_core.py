import pytest
from core.base_agent import BaseAgent


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

        agent = MockAgent()
        assert agent.name == "test_agent"
        assert agent.schedule == "every 1 hour"