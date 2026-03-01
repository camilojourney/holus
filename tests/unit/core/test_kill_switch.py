"""Tests for holus.core.kill_switch module."""

from __future__ import annotations


class TestKillSwitch:
    """Test kill switch activation, deactivation, and scope checking."""

    def test_activate_agent_scope(self, mock_redis):
        """Activating kill switch for a specific agent sets the correct Redis key."""
        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        ks.activate(scope="marketing-agent", reason="Manual stop")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "marketing-agent" in str(call_args)

    def test_deactivate_agent_scope(self, mock_redis):
        """Deactivating kill switch deletes the correct Redis key."""
        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        ks.deactivate(scope="marketing-agent")

        mock_redis.delete.assert_called_once()

    def test_is_active_returns_false_when_not_set(self, mock_redis):
        """Kill switch should return False when no keys are set."""
        mock_redis.exists.return_value = 0  # 0 = key not found in Redis

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        assert not ks.is_active(agent_name="marketing-agent")

    def test_is_active_returns_true_for_global(self, mock_redis):
        """Global kill switch should block all agents."""
        # exists() returns 1 (truthy) for the global key
        mock_redis.exists.return_value = 1

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        assert ks.is_active(agent_name="marketing-agent")

    def test_status_returns_dict(self, mock_redis):
        """Status should return a dict of active kill switches."""
        mock_redis.scan_iter.return_value = []

        from holus.core.kill_switch import KillSwitch

        ks = KillSwitch(redis_client=mock_redis)
        status = ks.status()

        assert isinstance(status, dict)
