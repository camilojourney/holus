"""Tests for resilience utilities."""

import time

from holus.core.resilience import CircuitBreaker


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert not cb.is_open

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_success_resets(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert not cb.is_open  # Reset by success

    def test_recovery_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open
        time.sleep(0.15)
        assert not cb.is_open  # Recovered

    def test_status(self):
        cb = CircuitBreaker("api", failure_threshold=5)
        cb.record_failure()
        s = cb.status()
        assert s["name"] == "api"
        assert s["consecutive_failures"] == 1
        assert not s["is_open"]
