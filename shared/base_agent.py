"""
Shared Base Agent — re-exports from core.base_agent for backward compatibility.

The canonical implementation lives in core/base_agent.py.
Import from either ``shared.base_agent`` or ``core.base_agent``.
"""
from core.base_agent import BaseAgent, RunRecord  # noqa: F401

__all__ = ["BaseAgent", "RunRecord"]
