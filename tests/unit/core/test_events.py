"""Unit tests for the events system — EventType, HolusEvent, EventBus.

All tests mock Redis — no real connections needed.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import redis

from holus.core.events import EventBus, EventType, HolusEvent

# ---------------------------------------------------------------------------
# EventType
# ---------------------------------------------------------------------------


class TestEventType:
    """StrEnum basics."""

    def test_string_value(self):
        assert EventType.CONTENT_GENERATED == "content_generated"

    def test_is_str_subclass(self):
        assert isinstance(EventType.AGENT_CRASH, str)

    @pytest.mark.parametrize(
        "member",
        [
            EventType.CONTENT_GENERATED,
            EventType.PR_MERGED,
            EventType.WORKFLOW_OPTIMIZED,
            EventType.AGENT_CRASH,
            EventType.CROSS_PROJECT_INSIGHT,
        ],
    )
    def test_member_exists(self, member: EventType):
        assert member in EventType


# ---------------------------------------------------------------------------
# HolusEvent
# ---------------------------------------------------------------------------


class TestHolusEvent:
    """Model creation and serialization."""

    def _make_event(self, **overrides) -> HolusEvent:
        defaults = {
            "source_agent": "test-agent",
            "event_type": EventType.CONTENT_GENERATED,
        }
        defaults.update(overrides)
        return HolusEvent(**defaults)

    def test_defaults(self):
        ev = self._make_event()
        assert ev.event_id  # auto-generated uuid hex
        assert len(ev.event_id) == 32
        assert ev.source_agent == "test-agent"
        assert ev.event_type == EventType.CONTENT_GENERATED
        assert isinstance(ev.timestamp, datetime)
        assert ev.payload == {}
        assert ev.correlation_id is None

    def test_custom_fields(self):
        ev = self._make_event(
            event_id="abc123",
            payload={"key": "value"},
            correlation_id="corr-1",
        )
        assert ev.event_id == "abc123"
        assert ev.payload == {"key": "value"}
        assert ev.correlation_id == "corr-1"

    def test_to_json_roundtrip(self):
        ev = self._make_event(payload={"score": 0.95})
        json_str = ev.to_json()
        restored = HolusEvent.from_json(json_str)
        assert restored.event_id == ev.event_id
        assert restored.source_agent == ev.source_agent
        assert restored.event_type == ev.event_type
        assert restored.payload == {"score": 0.95}

    def test_from_json_bytes(self):
        ev = self._make_event()
        json_bytes = ev.to_json().encode()
        restored = HolusEvent.from_json(json_bytes)
        assert restored.event_id == ev.event_id

    def test_to_json_is_valid_json(self):
        ev = self._make_event(payload={"nested": {"a": 1}})
        parsed = json.loads(ev.to_json())
        assert parsed["source_agent"] == "test-agent"
        assert parsed["payload"]["nested"]["a"] == 1

    def test_from_json_invalid_raises(self):
        with pytest.raises(ValueError):
            HolusEvent.from_json("not valid json")

    def test_timestamp_is_utc(self):
        ev = self._make_event()
        assert ev.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# EventBus — publish
# ---------------------------------------------------------------------------


class TestEventBusPublish:
    """Publish sends to both pub/sub and stream."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            yield bus

    def test_publish_calls_pubsub_and_stream(self, bus):
        ev = HolusEvent(
            source_agent="marketing",
            event_type=EventType.CONTENT_GENERATED,
        )
        bus.publish("holus.marketing.content", ev)

        r = bus._mock_redis
        r.publish.assert_called_once_with("holus.marketing.content", ev.to_json())
        r.xadd.assert_called_once_with(
            "holus:stream:holus.marketing.content",
            {"data": ev.to_json()},
            maxlen=EventBus.STREAM_MAX_LEN,
        )

    def test_publish_redis_error_does_not_raise(self, bus):
        bus._mock_redis.publish.side_effect = redis.RedisError("connection lost")
        ev = HolusEvent(
            source_agent="marketing",
            event_type=EventType.CONTENT_GENERATED,
        )
        # Should not raise — fire-and-forget
        bus.publish("holus.marketing.content", ev)

    def test_publish_stream_maxlen(self, bus):
        """Stream uses STREAM_MAX_LEN as rolling window."""
        ev = HolusEvent(
            source_agent="test",
            event_type=EventType.HEALTH_CHECK,
        )
        bus.publish("holus.system.health", ev)
        _, kwargs = bus._mock_redis.xadd.call_args
        assert kwargs["maxlen"] == 10_000


# ---------------------------------------------------------------------------
# EventBus — subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestEventBusSubscribe:
    """Subscription lifecycle."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_pubsub = MagicMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            bus._mock_pubsub = mock_pubsub
            yield bus

    def test_subscribe_creates_pubsub(self, bus):
        callback = MagicMock()
        bus.subscribe(["holus.marketing.content"], callback)
        bus._mock_redis.pubsub.assert_called_once()

    def test_subscribe_registers_channels(self, bus):
        callback = MagicMock()
        bus.subscribe(["chan1", "chan2"], callback)
        subscribe_calls = bus._mock_pubsub.subscribe.call_args_list
        assert len(subscribe_calls) == 2

    def test_subscribe_starts_listener_thread(self, bus):
        callback = MagicMock()
        bus.subscribe(["chan1"], callback)
        bus._mock_pubsub.run_in_thread.assert_called_once_with(
            sleep_time=0.1, daemon=True
        )

    def test_unsubscribe_stops_thread(self, bus):
        callback = MagicMock()
        bus.subscribe(["chan1"], callback)
        thread_mock = bus._mock_pubsub.run_in_thread.return_value
        bus.unsubscribe()
        bus._mock_pubsub.unsubscribe.assert_called_once()
        thread_mock.stop.assert_called_once()

    def test_unsubscribe_no_subscription_is_noop(self, bus):
        # No subscribe called yet — should not raise
        bus.unsubscribe()

    def test_handler_dispatches_event(self, bus):
        """Verify the internal handler parses messages and calls callback."""
        received = []

        def cb(channel, event):
            received.append((channel, event))

        bus.subscribe(["chan1"], cb)

        # Extract the handler registered with subscribe
        handler_kwargs = bus._mock_pubsub.subscribe.call_args[1]
        handler = handler_kwargs["chan1"]

        # Simulate a Redis message
        ev = HolusEvent(
            source_agent="test",
            event_type=EventType.HEALTH_CHECK,
        )
        handler({"type": "message", "channel": "chan1", "data": ev.to_json()})

        assert len(received) == 1
        assert received[0][0] == "chan1"
        assert received[0][1].event_type == EventType.HEALTH_CHECK

    def test_handler_ignores_non_message_types(self, bus):
        received = []
        bus.subscribe(["chan1"], lambda ch, ev: received.append(ev))

        handler_kwargs = bus._mock_pubsub.subscribe.call_args[1]
        handler = handler_kwargs["chan1"]

        # "subscribe" confirmation message — should be ignored
        handler({"type": "subscribe", "channel": "chan1", "data": 1})
        assert len(received) == 0

    def test_handler_malformed_data_does_not_raise(self, bus):
        bus.subscribe(["chan1"], MagicMock())

        handler_kwargs = bus._mock_pubsub.subscribe.call_args[1]
        handler = handler_kwargs["chan1"]

        # Invalid JSON — should log warning, not raise
        handler({"type": "message", "channel": "chan1", "data": "not json"})


# ---------------------------------------------------------------------------
# EventBus — read_stream
# ---------------------------------------------------------------------------


class TestEventBusReadStream:
    """Stream reading for coordinator replay."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            yield bus

    def test_read_stream_parses_events(self, bus):
        ev1 = HolusEvent(source_agent="a1", event_type=EventType.PR_MERGED)
        ev2 = HolusEvent(source_agent="a2", event_type=EventType.CI_FAILURE)
        bus._mock_redis.xrange.return_value = [
            ("1-0", {"data": ev1.to_json()}),
            ("2-0", {"data": ev2.to_json()}),
        ]

        events = bus.read_stream("holus.coding.prs")
        assert len(events) == 2
        assert events[0].source_agent == "a1"
        assert events[1].event_type == EventType.CI_FAILURE

    def test_read_stream_uses_correct_key(self, bus):
        bus._mock_redis.xrange.return_value = []
        bus.read_stream("holus.marketing.content", since="0-0", count=50)
        bus._mock_redis.xrange.assert_called_once_with(
            "holus:stream:holus.marketing.content", min="0-0", count=50
        )

    def test_read_stream_defaults(self, bus):
        bus._mock_redis.xrange.return_value = []
        bus.read_stream("chan")
        bus._mock_redis.xrange.assert_called_once_with(
            "holus:stream:chan", min="-", count=500
        )

    def test_read_stream_redis_error_returns_empty(self, bus):
        bus._mock_redis.xrange.side_effect = redis.RedisError("timeout")
        events = bus.read_stream("chan")
        assert events == []

    def test_read_stream_skips_malformed_entries(self, bus):
        ev = HolusEvent(source_agent="good", event_type=EventType.HEALTH_CHECK)
        bus._mock_redis.xrange.return_value = [
            ("1-0", {"data": "not json"}),
            ("2-0", {"data": ev.to_json()}),
        ]
        events = bus.read_stream("chan")
        assert len(events) == 1
        assert events[0].source_agent == "good"

    def test_read_stream_empty_stream(self, bus):
        bus._mock_redis.xrange.return_value = []
        assert bus.read_stream("chan") == []


# ---------------------------------------------------------------------------
# EventBus — read_streams_since
# ---------------------------------------------------------------------------


class TestEventBusReadStreamsSince:
    """Multi-channel time-based reading."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            yield bus

    def test_reads_multiple_channels(self, bus):
        bus._mock_redis.xrange.return_value = []
        result = bus.read_streams_since(["chan1", "chan2", "chan3"], since_hours=24)
        assert set(result.keys()) == {"chan1", "chan2", "chan3"}
        assert bus._mock_redis.xrange.call_count == 3

    def test_since_hours_calculates_cutoff(self, bus):
        bus._mock_redis.xrange.return_value = []
        with patch("time.time", return_value=1_000_000.0):
            bus.read_streams_since(["chan1"], since_hours=1)

        # cutoff_ms = (1_000_000 - 3600) * 1000 = 996_400_000
        expected_since = "996400000-0"
        bus._mock_redis.xrange.assert_called_once_with(
            "holus:stream:chan1", min=expected_since, count=500
        )

    def test_returns_events_per_channel(self, bus):
        ev = HolusEvent(source_agent="a1", event_type=EventType.WEEKLY_REPORT)

        def xrange_side_effect(key, **kwargs):
            if "chan1" in key:
                return [("1-0", {"data": ev.to_json()})]
            return []

        bus._mock_redis.xrange.side_effect = xrange_side_effect
        result = bus.read_streams_since(["chan1", "chan2"])
        assert len(result["chan1"]) == 1
        assert len(result["chan2"]) == 0


# ---------------------------------------------------------------------------
# EventBus — ping
# ---------------------------------------------------------------------------


class TestEventBusPing:
    """Health check."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            yield bus

    def test_ping_success(self, bus):
        bus._mock_redis.ping.return_value = True
        assert bus.ping() is True

    def test_ping_redis_error_returns_false(self, bus):
        bus._mock_redis.ping.side_effect = redis.RedisError("unreachable")
        assert bus.ping() is False


# ---------------------------------------------------------------------------
# EventBus — close
# ---------------------------------------------------------------------------


class TestEventBusClose:
    """Resource cleanup."""

    @pytest.fixture()
    def bus(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_pubsub = MagicMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_from_url.return_value = mock_redis
            bus = EventBus("redis://localhost:6379")
            bus._mock_redis = mock_redis
            bus._mock_pubsub = mock_pubsub
            yield bus

    def test_close_calls_unsubscribe_and_redis_close(self, bus):
        bus.subscribe(["chan1"], MagicMock())
        bus.close()
        bus._mock_pubsub.unsubscribe.assert_called()
        bus._mock_redis.close.assert_called_once()

    def test_close_without_subscription(self, bus):
        bus.close()
        bus._mock_redis.close.assert_called_once()

    def test_close_redis_error_does_not_raise(self, bus):
        bus._mock_redis.close.side_effect = redis.RedisError("already closed")
        bus.close()  # Should not raise


# ---------------------------------------------------------------------------
# EventBus — init
# ---------------------------------------------------------------------------


class TestEventBusInit:
    """Constructor behavior."""

    def test_default_redis_url(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            EventBus()
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=True
            )

    def test_custom_redis_url(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            EventBus("redis://custom:6380")
            mock_from_url.assert_called_once_with(
                "redis://custom:6380", decode_responses=True
            )

    def test_initial_state(self):
        with patch("holus.core.events.redis.Redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            bus = EventBus()
            assert bus._pubsub is None
            assert bus._listener_thread is None
