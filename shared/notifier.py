"""Shared notifier — re-exports from canonical core module."""
from core.notifier import Notifier, TelegramNotifier

__all__ = ["Notifier", "TelegramNotifier"]
