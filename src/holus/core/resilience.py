"""Resilience utilities — retry, fallback, circuit breaker.

Provides decorators and utilities for making LLM calls resilient
to transient failures, rate limits, and model unavailability.

Usage::

    from holus.core.resilience import with_retry, with_fallback_chain

    # Retry with exponential backoff
    @with_retry(max_attempts=3, backoff_base=2.0)
    async def call_llm(prompt: str) -> str: ...

    # Multi-model fallback chain
    result = await with_fallback_chain(
        prompt="...",
        models=["anthropic/claude-opus-4-6", "anthropic/claude-sonnet-4-6", "anthropic/claude-haiku-4-5-20251001"],
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from functools import wraps
from typing import Any, TypeVar

import requests

logger = logging.getLogger(__name__)

T = TypeVar("T")

PROXY_URL = "http://localhost:8080/v1/chat/completions"
PROXY_HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer local"}


def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    max_backoff: float = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
):
    """Decorator: retry with exponential backoff on transient failures."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    wait = min(backoff_base ** attempt, max_backoff)
                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt + 1, max_attempts, exc, wait,
                    )
                    await asyncio.sleep(wait)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


async def with_fallback_chain(
    *,
    system: str,
    user: str,
    models: list[str],
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str | None:
    """Try multiple models in order until one succeeds.

    Falls through the chain: Opus → Sonnet → Haiku → None.
    Each model gets one attempt (no retry within the chain).
    """
    for model in models:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            resp = requests.post(
                PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            logger.info("Fallback chain: %s succeeded", model)
            return result
        except Exception as exc:
            logger.warning("Fallback chain: %s failed (%s), trying next", model, exc)
            continue

    logger.error("Fallback chain: all %d models failed", len(models))
    return None


class CircuitBreaker:
    """Simple circuit breaker for external service calls.

    Opens after `failure_threshold` consecutive failures.
    Closes after `recovery_timeout` seconds.
    While open, calls fail immediately (no actual request).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure_time: float = 0.0
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)."""
        if not self._is_open:
            return False

        # Check if recovery timeout has elapsed
        if time.time() - self._last_failure_time >= self.recovery_timeout:
            logger.info("Circuit breaker %s: recovery timeout elapsed, half-opening", self.name)
            self._is_open = False
            self._failures = 0
            return False

        return True

    def record_success(self) -> None:
        """Record a successful call — resets failure count."""
        self._failures = 0
        self._is_open = False

    def record_failure(self) -> None:
        """Record a failed call — may open the circuit."""
        self._failures += 1
        self._last_failure_time = time.time()

        if self._failures >= self.failure_threshold:
            self._is_open = True
            logger.warning(
                "Circuit breaker %s: OPENED after %d failures (recovery in %.0fs)",
                self.name, self._failures, self.recovery_timeout,
            )

    def status(self) -> dict[str, Any]:
        """Return circuit breaker status."""
        return {
            "name": self.name,
            "is_open": self.is_open,
            "consecutive_failures": self._failures,
            "threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }
