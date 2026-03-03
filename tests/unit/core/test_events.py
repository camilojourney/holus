"""Tests for holus.core.events — EventType, HolusEvent, and EventBus."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from holus.core.events import EventBus, EventType, HolusEvent

# ---------------------------------------------------------------------------
# HolusEvent
# ---------------------------------------------------------------------------


class TestHolusEvent:
    def test_defaults_are_set(self) -> None:
        event = HolusEvent(
            source_agent="test-agent",
            event_type=EventType.CONTENT_GENERATED,
        )
        assert event.source_agent == "test-agent"
        assert event.event_type == EventType.CONTENT_GENERATED
        assert event.event_id  # non-empty
        assert isinstance(event.timestamp, datetime)
        assert event.payload == {}
        assert event.correlation_id is None

    def test_roundtrip_json(self) -> None:
        event = HolusEvent(
            source_agent="builder",
            event_type=EventType.PR_MERGED,
            payload={"pr": 42},
            correlation_id="abc123",
        )
        raw = event.to_json()
        restored = HolusEvent.from_json(raw)
        assert restored.event_id == event.event_id
        assert restored.source_agent == "builder"
        assert restored.event_type == EventType.PR_MERGED
        assert restored.payload == {"pr": 42}
        assert restored.correlation_id == "abc123"

    def test_from_json_bytes(self) -> None:
        event = HolusEvent(
            source_agent="tester",
            event_type=EventType.HEALTH_CHECK,
        )
        raw_bytes = event.to_json().encode()
        restored = HolusEvent.from_json(raw_bytes)
        assert restored.event_id == event.event_id

    def test_unique_event_ids(self) -> None:
        e1 = HolusEvent(source_agent="a", event_type=EventType.HEALTH_CHECK)
        e2 = HolusEvent(source_agent="a", event_type=EventType.HEALTH_CHECK)
        assert e1.event_id != e2.event_id


# ---------------------------------------------------------------------------
# EventBus — publish
# ---------------------------------------------------------------------------


class TestEventBusPing:
    def _make_bus(self) -> tuple[EventBus, MagicMock]:
        mock_redis = MagicMock()
        with patch("holus.core.events.redis.Redis.from_url", return_value=mock_redis):
            bus = EventBus("redis://localhost:6379")
        return bus, mock_redis

    def test_ping_returns_true_when_redis_ok(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_redis.ping.return_value = True
        assert bus.ping() is True

    def test_ping_returns_false_on_redis_error(self) -> None:
        import redis

        bus, mock_redis = self._make_bus()
        mock_redis.ping.side_effect = redis.RedisError("down")
        assert bus.ping() is False

    def test_publish_calls_redis_publish_and_xadd(self) -> None:
        bus, mock_redis = self._make_bus()
        event = HolusEvent(source_agent="sentinel", event_type=EventType.AGENT_CRASH)
        bus.publish("holus.system.crash", event)

        mock_redis.publish.assert_called_once()
        channel_arg = mock_redis.publish.call_args[0][0]
        assert channel_arg == "holus.system.crash"

        mock_redis.xadd.assert_called_once()
        xadd_key = mock_redis.xadd.call_args[0][0]
        assert xadd_key == "holus:stream:holus.system.crash"

    def test_publish_swallows_redis_error(self) -> None:
        import redis

        bus, mock_redis = self._make_bus()
        mock_redis.publish.side_effect = redis.RedisError("boom")
        event = HolusEvent(source_agent="a", event_type=EventType.HEALTH_CHECK)
        # Should not raise
        bus.publish("holus.system.health", event)

    def test_read_stream_returns_events(self) -> None:
        bus, mock_redis = self._make_bus()
        event = HolusEvent(
            source_agent="reader",
            event_type=EventType.WEEKLY_SYNTHESIS,
        )
        mock_redis.xrange.return_value = [
            ("1234-0", {"data": event.to_json()}),
        ]
        result = bus.read_stream("holus.system.weekly")
        assert len(result) == 1
        assert result[0].event_id == event.event_id

    def test_read_stream_returns_empty_on_redis_error(self) -> None:
        import redis

        bus, mock_redis = self._make_bus()
        mock_redis.xrange.side_effect = redis.RedisError("gone")
        result = bus.read_stream("holus.system.weekly")
        assert result == []
