"""Tests for holus.core.health.acquire_run_lock context manager."""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from holus.core.health import acquire_run_lock

# ---------------------------------------------------------------------------
# Basic lock acquisition
# ---------------------------------------------------------------------------


class TestAcquireRunLock:
    def test_acquires_lock_without_error(self, tmp_path: Path) -> None:
        """Lock is acquired and released with no exception."""
        lock_path = tmp_path / "test.lock"
        with acquire_run_lock(lock_path=lock_path):
            assert lock_path.exists()

    def test_creates_lock_directory_if_missing(self, tmp_path: Path) -> None:
        """Parent directory is created if it does not exist."""
        lock_path = tmp_path / "deep" / "nested" / "test.lock"
        assert not lock_path.parent.exists()

        with acquire_run_lock(lock_path=lock_path):
            assert lock_path.parent.exists()

    def test_yields_file_descriptor(self, tmp_path: Path) -> None:
        """The context manager yields a file-like object."""
        lock_path = tmp_path / "test.lock"
        with acquire_run_lock(lock_path=lock_path) as fd:
            assert fd is not None
            assert hasattr(fd, "write")

    def test_lock_released_after_exit(self, tmp_path: Path) -> None:
        """After the context exits, the lock can be re-acquired."""
        lock_path = tmp_path / "test.lock"

        with acquire_run_lock(lock_path=lock_path):
            pass

        # Must be able to acquire again after first context exits
        with acquire_run_lock(lock_path=lock_path):
            assert lock_path.exists()

    def test_default_lock_path(self) -> None:
        """Calling with no arguments uses the default path without error."""
        # Just verify we can enter and exit cleanly (default path in /tmp)
        with acquire_run_lock():
            pass  # default path acquired and released


# ---------------------------------------------------------------------------
# Conflict detection (BlockingIOError on concurrent lock)
# ---------------------------------------------------------------------------


def _try_acquire_lock(lock_path_str: str, result_queue: multiprocessing.Queue) -> None:
    """Subprocess helper: tries to acquire lock, reports result."""
    from holus.core.health import acquire_run_lock

    lock_path = Path(lock_path_str)
    try:
        with acquire_run_lock(lock_path=lock_path):
            result_queue.put("acquired")
    except BlockingIOError:
        result_queue.put("blocked")
    except Exception as exc:
        result_queue.put(f"error:{type(exc).__name__}:{exc}")


class TestAcquireRunLockConflict:
    def test_raises_blocking_io_error_when_locked(self, tmp_path: Path) -> None:
        """Second acquire on same path raises BlockingIOError."""
        lock_path = tmp_path / "marketing.lock"
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        with acquire_run_lock(lock_path=lock_path):
            # Try to acquire from a subprocess while we hold the lock
            proc = multiprocessing.Process(
                target=_try_acquire_lock,
                args=(str(lock_path), result_queue),
            )
            proc.start()
            proc.join(timeout=5)

            result = result_queue.get(timeout=2)
            assert result == "blocked", f"Expected blocked, got: {result}"

    def test_different_paths_do_not_conflict(self, tmp_path: Path) -> None:
        """Two different lock paths can be held simultaneously."""
        path_a = tmp_path / "a.lock"
        path_b = tmp_path / "b.lock"

        with acquire_run_lock(lock_path=path_a), acquire_run_lock(lock_path=path_b):
            assert path_a.exists()
            assert path_b.exists()
