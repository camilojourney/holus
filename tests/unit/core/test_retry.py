"""Tests for holus.core.retry — retry_with_backoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from holus.core.retry import TRANSIENT_EXCEPTIONS, retry_with_backoff

# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestRetrySuccess:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        """Function that succeeds immediately is called exactly once."""
        mock_fn = AsyncMock(return_value="ok")

        result = await retry_with_backoff(mock_fn)

        assert result == "ok"
        assert mock_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_correct_value(self) -> None:
        """Return value from the wrapped callable is passed through unchanged."""
        mock_fn = AsyncMock(return_value={"data": [1, 2, 3]})

        result = await retry_with_backoff(mock_fn)

        assert result == {"data": [1, 2, 3]}


# ---------------------------------------------------------------------------
# Transient retry path
# ---------------------------------------------------------------------------


class TestRetryTransient:
    @pytest.mark.asyncio
    async def test_retries_on_timeout(self) -> None:
        """TimeoutError triggers a retry; succeeds on second attempt."""
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("connection timed out")
            return "recovered"

        with patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(flaky, max_retries=3, base_delay=0.01)

        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_httpx_timeout(self) -> None:
        """httpx.TimeoutException triggers a retry."""
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ReadTimeout("read timed out", request=None)  # type: ignore[arg-type]
            return "done"

        with patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(flaky, max_retries=3, base_delay=0.01)

        assert result == "done"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self) -> None:
        """Delay doubles between each retry attempt."""
        delays: list[float] = []

        async def always_fails() -> None:
            raise TimeoutError("always")

        async def mock_sleep(seconds: float) -> None:
            delays.append(seconds)

        with (
            patch("holus.core.retry.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(TimeoutError),
        ):
            await retry_with_backoff(always_fails, max_retries=3, base_delay=1.0)

        # With max_retries=3 and base_delay=1.0: delays are [1.0, 2.0]
        # (sleep is called between attempts, not after the final failure)
        assert delays == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_custom_base_delay(self) -> None:
        """base_delay parameter is respected."""
        delays: list[float] = []

        async def always_fails() -> None:
            raise ConnectionError("refused")

        async def mock_sleep(seconds: float) -> None:
            delays.append(seconds)

        with (
            patch("holus.core.retry.asyncio.sleep", side_effect=mock_sleep),
            pytest.raises(ConnectionError),
        ):
            await retry_with_backoff(always_fails, max_retries=3, base_delay=0.5)

        assert delays == [0.5, 1.0]


# ---------------------------------------------------------------------------
# Max retries exceeded
# ---------------------------------------------------------------------------


class TestRetryMaxExceeded:
    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """Last exception is raised when all retries are exhausted."""
        mock_fn = AsyncMock(side_effect=TimeoutError("permanent timeout"))

        with (
            patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError, match="permanent timeout"),
        ):
            await retry_with_backoff(mock_fn, max_retries=3)

        assert mock_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_one_calls_once(self) -> None:
        """max_retries=1 means a single attempt with no retries."""
        mock_fn = AsyncMock(side_effect=TimeoutError("fail"))

        with (
            patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(TimeoutError),
        ):
            await retry_with_backoff(mock_fn, max_retries=1)

        assert mock_fn.call_count == 1
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Non-transient exceptions — no retry
# ---------------------------------------------------------------------------


class TestRetryNonTransient:
    @pytest.mark.asyncio
    async def test_non_transient_raises_immediately(self) -> None:
        """ValueError is not a transient exception; raised without retry."""
        call_count = 0

        async def bad_fn() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("programming error")

        with (
            patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(ValueError, match="programming error"),
        ):
            await retry_with_backoff(bad_fn, max_retries=3)

        assert call_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_transient_exceptions(self) -> None:
        """Custom transient_exceptions tuple overrides the default."""
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("custom transient")
            return "ok"

        with patch("holus.core.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(
                flaky,
                max_retries=3,
                transient_exceptions=(ValueError,),
            )

        assert result == "ok"
        assert call_count == 2


# ---------------------------------------------------------------------------
# TRANSIENT_EXCEPTIONS constant
# ---------------------------------------------------------------------------


class TestTransientExceptions:
    def test_contains_expected_types(self) -> None:
        """TRANSIENT_EXCEPTIONS includes the expected httpx and builtins."""
        assert httpx.TimeoutException in TRANSIENT_EXCEPTIONS
        assert httpx.ConnectError in TRANSIENT_EXCEPTIONS
        assert httpx.RemoteProtocolError in TRANSIENT_EXCEPTIONS
        assert ConnectionError in TRANSIENT_EXCEPTIONS
        assert TimeoutError in TRANSIENT_EXCEPTIONS
