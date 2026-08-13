"""Small local-only primitives for durable current-state projections."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Write, fsync, replace, and fsync the containing directory.

    Callers retain their own domain lock/CAS policy; this primitive guarantees
    readers observe either the old complete file or the new complete file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
