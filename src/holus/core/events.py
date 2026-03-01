"""Redis-backed event bus for inter-agent communication.

Architecture:
  - Redis Pub/Sub for real-time notifications.
  - Redis Streams for persistent, replayable event history.
  - Agents publish domain events; they never read another agent's state directly.
  - The coordinator subscribes to all channels for daily cross-project synthesis.

Each channel is namespaced: ``holus.{domain}.{category}``
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import redis
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class EventType(StrEnum):
    """Canonical event types published across the Holus event bus."""

    # Marketing
    CONTENT_GENERATED = "content_generated"
    CONTENT_APPROVED = "content_approved"
    CONTENT_PUBLISHED = "content_published"
    STRATEGY_UPDATED = "strategy_updated"
    WEEKLY_REPORT = "weekly_report"

    # Coding
    PR_MERGED = "pr_merged"
    CI_FAILURE = "ci_failure"
    DEPENDENCY_ALERT = "dependency_alert"
    SELF_IMPROVEMENT_CYCLE = "self_improvement_cycle"
    CODE_REVIEWED = "code_reviewed"

    # Pilaster
    WORKFLOW_OPTIMIZED = "workflow_optimized"
    QUALITY_THRESHOLD_MET = "quality_threshold_met"
    GENERATION_BATCH_COMPLETE = "generation_batch_complete"

    # System
    AGENT_CRASH = "agent_crash"
    GUARDRAIL_VIOLATION = "guardrail_violation"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    HEALTH_CHECK = "health_check"

    # Coordinator
    CROSS_PROJECT_INSIGHT = "cross_project_insight"
    RESOURCE_REALLOCATION = "resource_reallocation"
    RISK_ESCALATION = "risk_escalation"
    WEEKLY_SYNTHESIS = "weekly_synthesis"


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class HolusEvent(BaseModel):
    """A single event on the Holus event bus."""

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    source_agent: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str | bytes) -> HolusEvent:
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class EventBus:
    """Redis-backed publish/subscribe + streams event bus.

    Usage::

        bus = EventBus("redis://localhost:6379")

        # Publish (fire-and-forget)
        bus.publish("holus.marketing.content", event)

        # Subscribe (callback-based, runs in background thread)
        bus.subscribe(["holus.marketing.content"], my_handler)

        # Read from stream (for coordinator daily replay)
        events = bus.read_stream("holus.marketing.content", since="-", count=100)
    """

    STREAM_MAX_LEN = 10_000  # Rolling window per channel

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._pubsub: redis.client.PubSub | None = None
        self._listener_thread: threading.Thread | None = None

    # -- Publishing ----------------------------------------------------------

    def publish(self, channel: str, event: HolusEvent) -> None:
        """Publish an event to both Pub/Sub (real-time) and Streams (persistent).

        This is fire-and-forget from the publisher's perspective -- it never
        blocks the publishing agent.
        """
        payload = event.to_json()
        try:
            # Real-time notification
            self._redis.publish(channel, payload)

            # Persistent stream for replay (used by the coordinator)
            stream_key = f"holus:stream:{channel}"
            self._redis.xadd(
                stream_key,
                {"data": payload},
                maxlen=self.STREAM_MAX_LEN,
            )
        except redis.RedisError:
            logger.exception("Failed to publish event to %s", channel)

    # -- Subscribing (real-time) --------------------------------------------

    def subscribe(
        self,
        channels: list[str],
        callback: Callable[[str, HolusEvent], None],
    ) -> None:
        """Subscribe to one or more channels with a callback.

        The callback receives ``(channel, event)`` and runs in a background
        daemon thread.
        """
        self._pubsub = self._redis.pubsub()

        def _handler(message: dict[str, Any]) -> None:
            if message["type"] != "message":
                return
            try:
                event = HolusEvent.from_json(message["data"])
                callback(message["channel"], event)
            except Exception:
                logger.exception("Error processing event on %s", message.get("channel"))

        for ch in channels:
            self._pubsub.subscribe(**{ch: _handler})

        self._listener_thread = self._pubsub.run_in_thread(
            sleep_time=0.1,
            daemon=True,
        )

    def unsubscribe(self) -> None:
        """Stop all subscriptions."""
        if self._pubsub is not None:
            self._pubsub.unsubscribe()
        if self._listener_thread is not None:
            self._listener_thread.stop()
            self._listener_thread = None

    # -- Stream reading (for coordinator replay) ----------------------------

    def read_stream(
        self,
        channel: str,
        *,
        since: str = "-",
        count: int = 500,
    ) -> list[HolusEvent]:
        """Read events from the persistent Redis Stream.

        Args:
            channel: The logical channel name.
            since: Stream ID to start from.  ``"-"`` means the beginning;
                   pass the last-seen ID for incremental reads.
            count: Maximum number of events to return.

        Returns:
            A list of ``HolusEvent`` instances ordered by stream time.
        """
        stream_key = f"holus:stream:{channel}"
        try:
            raw = self._redis.xrange(stream_key, min=since, count=count)
        except redis.RedisError:
            logger.exception("Failed to read stream %s", stream_key)
            return []

        events: list[HolusEvent] = []
        for _stream_id, fields in raw:
            try:
                events.append(HolusEvent.from_json(fields["data"]))
            except Exception:
                logger.warning("Skipping malformed event in %s", stream_key)
        return events

    def read_streams_since(
        self,
        channels: list[str],
        since_hours: int = 24,
    ) -> dict[str, list[HolusEvent]]:
        """Read events from multiple streams within the last *since_hours*.

        Convenience wrapper used by the coordinator's daily synthesis.
        """
        import time

        cutoff_ms = int((time.time() - since_hours * 3600) * 1000)
        since_id = f"{cutoff_ms}-0"

        result: dict[str, list[HolusEvent]] = {}
        for ch in channels:
            result[ch] = self.read_stream(ch, since=since_id)
        return result

    # -- Health check --------------------------------------------------------

    def ping(self) -> bool:
        """Return ``True`` if the Redis backend is reachable."""
        try:
            return self._redis.ping()
        except redis.RedisError:
            return False

    def close(self) -> None:
        """Release resources."""
        self.unsubscribe()
        try:
            self._redis.close()
        except redis.RedisError:
            logger.debug("Redis already closed or unavailable")
