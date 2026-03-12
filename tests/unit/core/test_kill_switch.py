"""Tests for holus.core.kill_switch module."""

from __future__ import annotations

from unittest.mock import MagicMock

from holus.core.kill_switch import KillSwitch, KillSwitchMode


def _redis_with_store() -> MagicMock:
    store: dict[str, str] = {}
    redis = MagicMock()
    redis.set.side_effect = lambda key, value: store.__setitem__(key, value) or True
    redis.get.side_effect = lambda key: store.get(key)
    redis.delete.side_effect = lambda key: 1 if store.pop(key, None) is not None else 0
    redis.scan_iter.side_effect = lambda match=None: list(store.keys())
    return redis


class TestKillSwitch:
    """Test kill switch activation, deactivation, and scope checking."""

    def test_activate_agent_scope(self) -> None:
        """Activating a kill switch stores the expected payload."""
        redis = _redis_with_store()

        ks = KillSwitch(redis_client=redis)
        ks.activate(scope="marketing-agent", reason="Manual stop")

        assert redis.set.called
        saved_key = redis.set.call_args.args[0]
        assert saved_key == "holus:kill:agent:marketing-agent"

    def test_deactivate_agent_scope(self) -> None:
        """Deactivating a kill switch removes the key."""
        redis = _redis_with_store()
        ks = KillSwitch(redis_client=redis)
        ks.activate(scope="marketing-agent", reason="Manual stop")

        ks.deactivate(scope="marketing-agent")

        assert redis.delete.called
        assert redis.get("holus:kill:agent:marketing-agent") is None

    def test_is_active_returns_false_when_not_set(self) -> None:
        """Kill switch should return False when no keys are set."""
        ks = KillSwitch(redis_client=_redis_with_store())

        assert not ks.is_active(agent_name="marketing-agent")

    def test_is_active_returns_true_for_global_pause(self) -> None:
        """Global all-paused kill switch should block the marketing agent."""
        redis = _redis_with_store()
        ks = KillSwitch(redis_client=redis)
        ks.activate(scope="global", reason="Emergency", mode=KillSwitchMode.ALL_PAUSED)

        assert ks.is_active(agent_name="marketing-agent")

    def test_build_paused_does_not_block_content_cycle(self) -> None:
        """BUILD_PAUSED should stop builds without halting content agents."""
        redis = _redis_with_store()
        ks = KillSwitch(redis_client=redis)
        ks.activate(
            scope="global", reason="Pause self-improvement", mode=KillSwitchMode.BUILD_PAUSED
        )

        assert not ks.is_active(agent_name="marketing-agent")
        assert ks.builds_paused("global") is True

    def test_status_returns_dict(self) -> None:
        """Status should return a dict of active kill switches."""
        redis = _redis_with_store()
        ks = KillSwitch(redis_client=redis)
        ks.activate(scope="marketing-agent", reason="Manual stop")

        status = ks.status()

        assert isinstance(status, dict)
        assert "holus:kill:agent:marketing-agent" in status
