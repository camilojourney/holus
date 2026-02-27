"""File-based run lock to prevent overlapping agent runs.

Uses OS-level ``flock`` which auto-releases on crash — no stale locks.

Usage::

    from holus.core.run_lock import acquire_run_lock

    with acquire_run_lock("holus-marketing"):
        # Only one process can hold this lock at a time
        await agent.run()
"""

from __future__ import annotations

import fcntl
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


@contextmanager
def acquire_run_lock(
    agent_name: str,
    lock_dir: Path = Path("/tmp/holus"),
) -> Generator[None, None, None]:
    """Prevent overlapping runs of the same agent.

    Uses OS-level flock which auto-releases on crash.

    Args:
        agent_name: Unique identifier for the lock (e.g. "holus-marketing").
        lock_dir: Directory for lock files.

    Yields:
        None when lock is acquired.

    Raises:
        SystemExit: If another instance already holds the lock.
    """
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{agent_name}.lock"

    fd = open(lock_file, "w")  # noqa: SIM115
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(
            f"Agent {agent_name} is already running. Exiting.",
            file=sys.stderr,
        )
        fd.close()
        sys.exit(0)

    try:
        fd.write(str(os.getpid()))
        fd.flush()
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        lock_file.unlink(missing_ok=True)
