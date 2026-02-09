"""
Shared Notifier — re-exports from core.notifier for backward compatibility.

The canonical implementation lives in core/notifier.py.
"""
from core.notifier import Notifier, TelegramNotifier  # noqa: F401

__all__ = ["Notifier", "TelegramNotifier"]
