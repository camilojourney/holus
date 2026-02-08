"""Holus — Personal AI Agent Workforce

Shared code for all domains.
"""
__version__ = "0.1.0"

from .types import (
    ContentItem,
    ContentType,
    Platform,
    FunnelStage,
    PublishResult,
    Analytics,
    AgentMessage,
)
from .config import load_config, load_domain_config, merge_configs

__all__ = [
    "ContentItem",
    "ContentType",
    "Platform",
    "FunnelStage",
    "PublishResult",
    "Analytics",
    "AgentMessage",
    "load_config",
    "load_domain_config",
    "merge_configs",
]
