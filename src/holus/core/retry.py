"""Retry with exponential backoff for transient failures."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = structlog.get_logger()

# Transient exceptions that should trigger retry
TRANSIENT_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    ConnectionError,
    TimeoutError,
)


async def retry_with_backoff[T](
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    transient_exceptions: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> T:
    """Retry an async callable with exponential backoff on transient errors.

    Args:
        fn: Async callable to retry.
        max_retries: Maximum number of attempts (default: 3).
        base_delay: Initial delay in seconds before first retry (default: 1.0).
            Each subsequent retry doubles the delay (1s, 2s, 4s, ...).
        transient_exceptions: Exception types that trigger a retry.
            Non-transient exceptions are raised immediately without retry.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last transient exception if all retries are exhausted.
        Any non-transient exception immediately (no retry).

    Example::

        result = await retry_with_backoff(
            lambda: client.get("https://api.example.com/health"),
            max_retries=3,
            base_delay=1.0,
        )
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await fn()
        except transient_exceptions as exc:
            last_exc = exc
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "Transient error, retrying",
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]  # unreachable but makes mypy happy
