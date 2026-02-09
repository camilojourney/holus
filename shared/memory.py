"""
Shared Memory Store — re-exports from core.memory for backward compatibility.

The canonical implementation lives in core/memory.py.
"""
from core.memory import MemoryStore  # noqa: F401

__all__ = ["MemoryStore"]
