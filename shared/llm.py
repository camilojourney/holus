"""
Shared LLM Provider — re-exports from core.llm for backward compatibility.

The canonical implementation lives in core/llm.py.
"""
from core.llm import LLMProvider, TaskComplexity, load_llm_provider  # noqa: F401

__all__ = ["LLMProvider", "TaskComplexity", "load_llm_provider"]
