"""Tests for holus.core.kill_switch module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestKillSwitch:
    """Test kill switch activation, deactivation, and scope checking."""

    def test_activate_agent_scope(self, mock_redis):
        """Activating kill switch for a specific agent sets the correct Redis key."""
        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        ks.activate(scope="agent", target="trading_agent", reason="Manual stop")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "trading_agent" in str(call_args)

    def test_deactivate_agent_scope(self, mock_redis):
        """Deactivating kill switch deletes the correct Redis key."""
        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        ks.deactivate(scope="agent", target="trading_agent")

        mock_redis.delete.assert_called_once()

    def test_is_active_returns_false_when_not_set(self, mock_redis):
        """Kill switch should return False when no keys are set."""
        mock_redis.get.return_value = None

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        assert not ks.is_active(agent_name="trading_agent")

    def test_is_active_returns_true_for_global(self, mock_redis):
        """Global kill switch should block all agents."""
        # First call (agent-level) returns None, second (domain) returns None,
        # third (global) returns the kill data
        mock_redis.get.side_effect = [None, None, b'{"reason": "Emergency"}']

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        assert ks.is_active(agent_name="trading_agent")

    def test_status_returns_all_scopes(self, mock_redis):
        """Status should report on all three scope levels."""
        mock_redis.get.return_value = None

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        status = ks.status(agent_name="trading_agent")

        assert "agent" in status
        assert "domain" in status
        assert "global" in status
