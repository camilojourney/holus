"""
Shared Orchestrator — re-exports from core.orchestrator for backward compatibility.

The canonical implementation lives in core/orchestrator.py.
"""
from core.orchestrator import Orchestrator, parse_schedule  # noqa: F401

__all__ = ["Orchestrator", "parse_schedule"]
