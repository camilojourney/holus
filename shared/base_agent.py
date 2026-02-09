"""Shared base_agent — re-exports from canonical core module.

All agents should import from here or from core.base_agent directly.
This module exists for backward compatibility.
"""
from core.base_agent import BaseAgent, RunRecord

__all__ = ["BaseAgent", "RunRecord"]
