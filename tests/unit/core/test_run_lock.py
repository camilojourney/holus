"""Tests for holus.core.run_lock."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from holus.core.run_lock import acquire_run_lock


def test_acquire_run_lock_creates_lock_file(tmp_path: Path) -> None:
    """Lock file is created and contains the PID."""
    lock_dir = tmp_path / "locks"

    with acquire_run_lock("test-agent", lock_dir=lock_dir):
        lock_file = lock_dir / "test-agent.lock"
        assert lock_file.exists()
        assert lock_file.read_text() == str(os.getpid())


def test_lock_file_cleaned_up_after_exit(tmp_path: Path) -> None:
    """Lock file is removed after the context manager exits."""
    lock_dir = tmp_path / "locks"

    with acquire_run_lock("test-agent", lock_dir=lock_dir):
        pass

    lock_file = lock_dir / "test-agent.lock"
    assert not lock_file.exists()


def test_lock_dir_created_if_missing(tmp_path: Path) -> None:
    """Lock directory is created if it doesn't exist."""
    lock_dir = tmp_path / "deep" / "nested" / "locks"
    assert not lock_dir.exists()

    with acquire_run_lock("test-agent", lock_dir=lock_dir):
        assert lock_dir.exists()


def _try_second_lock(lock_dir_str: str, result_queue: multiprocessing.Queue) -> None:
    """Helper function to attempt acquiring a lock in a subprocess."""

    lock_dir = Path(lock_dir_str)
    try:
        with acquire_run_lock("test-agent", lock_dir=lock_dir):
            result_queue.put("acquired")
    except SystemExit as e:
        result_queue.put(f"exit:{e.code}")


def test_second_instance_blocked(tmp_path: Path) -> None:
    """A second process cannot acquire the same lock."""
    lock_dir = tmp_path / "locks"
    result_queue = multiprocessing.Queue()

    with acquire_run_lock("test-agent", lock_dir=lock_dir):
        # Try to acquire in a subprocess — should exit(0)
        proc = multiprocessing.Process(
            target=_try_second_lock,
            args=(str(lock_dir), result_queue),
        )
        proc.start()
        proc.join(timeout=5)

        result = result_queue.get(timeout=2)
        assert result == "exit:0", f"Expected clean exit, got: {result}"


def test_different_agents_not_blocked(tmp_path: Path) -> None:
    """Two different agent names can hold locks simultaneously."""
    lock_dir = tmp_path / "locks"

    with (
        acquire_run_lock("agent-a", lock_dir=lock_dir),
        acquire_run_lock("agent-b", lock_dir=lock_dir),
    ):
        # Both should be held simultaneously
        assert (lock_dir / "agent-a.lock").exists()
        assert (lock_dir / "agent-b.lock").exists()
