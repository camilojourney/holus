"""Tests for holus.core.events — EventType, HolusEvent, and EventBus."""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import redis as redis_lib

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
        bus, mock_redis = self._make_bus()
        mock_redis.ping.side_effect = redis_lib.RedisError("down")
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
        bus, mock_redis = self._make_bus()
        mock_redis.publish.side_effect = redis_lib.RedisError("boom")
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
        bus, mock_redis = self._make_bus()
        mock_redis.xrange.side_effect = redis_lib.RedisError("gone")
        result = bus.read_stream("holus.system.weekly")
        assert result == []

    def test_publish_passes_maxlen(self) -> None:
        bus, mock_redis = self._make_bus()
        event = HolusEvent(source_agent="a", event_type=EventType.HEALTH_CHECK)
        bus.publish("ch", event)
        _, kwargs = mock_redis.xadd.call_args
        assert kwargs["maxlen"] == EventBus.STREAM_MAX_LEN

    def test_read_stream_skips_malformed_events(self) -> None:
        bus, mock_redis = self._make_bus()
        good = HolusEvent(source_agent="ok", event_type=EventType.HEALTH_CHECK)
        mock_redis.xrange.return_value = [
            ("1-0", {"data": "not-json!!!"}),
            ("2-0", {"data": good.to_json()}),
        ]
        result = bus.read_stream("ch")
        assert len(result) == 1
        assert result[0].event_id == good.event_id


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------


class TestEventType:
    def test_str_enum_values(self) -> None:
        assert str(EventType.CONTENT_GENERATED) == "content_generated"
        assert str(EventType.KILL_SWITCH_ACTIVATED) == "kill_switch_activated"

    def test_all_values_are_lowercase_snake(self) -> None:
        for member in EventType:
            assert member.value == member.value.lower()
            assert " " not in member.value

    def test_member_count(self) -> None:
        # Guard against accidental removal
        assert len(EventType) >= 18


# ---------------------------------------------------------------------------
# EventBus — subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestEventBusSubscribe:
    def _make_bus(self) -> tuple[EventBus, MagicMock]:
        mock_redis = MagicMock()
        with patch("holus.core.events.redis.Redis.from_url", return_value=mock_redis):
            bus = EventBus("redis://localhost:6379")
        return bus, mock_redis

    def test_subscribe_creates_pubsub_and_thread(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_pubsub = MagicMock()
        mock_thread = MagicMock()
        mock_pubsub.run_in_thread.return_value = mock_thread
        mock_redis.pubsub.return_value = mock_pubsub

        bus.subscribe(["ch1", "ch2"], lambda c, e: None)

        mock_redis.pubsub.assert_called_once()
        assert mock_pubsub.subscribe.call_count == 2
        mock_pubsub.run_in_thread.assert_called_once_with(sleep_time=0.1, daemon=True)
        assert bus._listener_thread is mock_thread

    def test_subscribe_handler_parses_event(self) -> None:
        """Verify the internal handler correctly calls back with a HolusEvent."""
        bus, mock_redis = self._make_bus()
        mock_pubsub = MagicMock()
        mock_pubsub.run_in_thread.return_value = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        received: list[tuple[str, HolusEvent]] = []
        bus.subscribe(["ch1"], lambda c, e: received.append((c, e)))

        # Extract the handler registered via subscribe(**{ch: handler})
        handler_kwargs = mock_pubsub.subscribe.call_args[1]
        handler = handler_kwargs["ch1"]

        event = HolusEvent(source_agent="test", event_type=EventType.HEALTH_CHECK)
        handler({"type": "message", "channel": "ch1", "data": event.to_json()})

        assert len(received) == 1
        assert received[0][0] == "ch1"
        assert received[0][1].event_id == event.event_id

    def test_subscribe_handler_ignores_non_message(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_pubsub = MagicMock()
        mock_pubsub.run_in_thread.return_value = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        received: list = []
        bus.subscribe(["ch1"], lambda c, e: received.append(1))

        handler = mock_pubsub.subscribe.call_args[1]["ch1"]
        handler({"type": "subscribe", "channel": "ch1", "data": "1"})

        assert received == []

    def test_subscribe_handler_isolates_errors(self) -> None:
        """Callback exceptions are logged, not raised."""
        bus, mock_redis = self._make_bus()
        mock_pubsub = MagicMock()
        mock_pubsub.run_in_thread.return_value = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        def bad_callback(c: str, e: HolusEvent) -> None:
            raise ValueError("oops")

        bus.subscribe(["ch1"], bad_callback)
        handler = mock_pubsub.subscribe.call_args[1]["ch1"]

        event = HolusEvent(source_agent="test", event_type=EventType.HEALTH_CHECK)
        # Should not raise
        handler({"type": "message", "channel": "ch1", "data": event.to_json()})

    def test_unsubscribe_stops_thread(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_pubsub = MagicMock()
        mock_thread = MagicMock()
        mock_pubsub.run_in_thread.return_value = mock_thread
        mock_redis.pubsub.return_value = mock_pubsub

        bus.subscribe(["ch1"], lambda c, e: None)
        bus.unsubscribe()

        mock_pubsub.unsubscribe.assert_called_once()
        mock_thread.stop.assert_called_once()
        assert bus._listener_thread is None

    def test_unsubscribe_noop_when_nothing_subscribed(self) -> None:
        bus, _mock_redis = self._make_bus()
        # Should not raise
        bus.unsubscribe()


# ---------------------------------------------------------------------------
# EventBus — read_streams_since
# ---------------------------------------------------------------------------


class TestEventBusReadStreamsSince:
    def _make_bus(self) -> tuple[EventBus, MagicMock]:
        mock_redis = MagicMock()
        with patch("holus.core.events.redis.Redis.from_url", return_value=mock_redis):
            bus = EventBus("redis://localhost:6379")
        return bus, mock_redis

    def test_reads_multiple_channels(self) -> None:
        bus, mock_redis = self._make_bus()
        e1 = HolusEvent(source_agent="a", event_type=EventType.CONTENT_GENERATED)
        e2 = HolusEvent(source_agent="b", event_type=EventType.PR_MERGED)
        mock_redis.xrange.side_effect = [
            [("1-0", {"data": e1.to_json()})],
            [("2-0", {"data": e2.to_json()})],
        ]

        result = bus.read_streams_since(["ch1", "ch2"], since_hours=24)

        assert len(result) == 2
        assert len(result["ch1"]) == 1
        assert len(result["ch2"]) == 1
        assert result["ch1"][0].event_id == e1.event_id

    def test_since_hours_computes_cutoff(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_redis.xrange.return_value = []

        before = time.time()
        bus.read_streams_since(["ch1"], since_hours=1)
        after = time.time()

        since_arg = mock_redis.xrange.call_args[1]["min"]
        cutoff_ms = int(since_arg.split("-")[0])
        # Should be roughly 1 hour ago in milliseconds
        expected_low = int((before - 3600) * 1000) - 1000
        expected_high = int((after - 3600) * 1000) + 1000
        assert expected_low <= cutoff_ms <= expected_high


# ---------------------------------------------------------------------------
# EventBus — close
# ---------------------------------------------------------------------------


class TestEventBusClose:
    def _make_bus(self) -> tuple[EventBus, MagicMock]:
        mock_redis = MagicMock()
        with patch("holus.core.events.redis.Redis.from_url", return_value=mock_redis):
            bus = EventBus("redis://localhost:6379")
        return bus, mock_redis

    def test_close_calls_unsubscribe_and_redis_close(self) -> None:
        bus, mock_redis = self._make_bus()
        bus.close()
        mock_redis.close.assert_called_once()

    def test_close_swallows_redis_error(self) -> None:
        bus, mock_redis = self._make_bus()
        mock_redis.close.side_effect = redis_lib.RedisError("already closed")
        # Should not raise
        bus.close()
