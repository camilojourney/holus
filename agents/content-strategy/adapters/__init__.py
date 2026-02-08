"""Platform adapter registry."""
from typing import Type

from .base_adapter import BaseAdapter, Content, ContentType, PublishResult, Analytics
from .youtube_adapter import YouTubeAdapter
from .twitter_adapter import TwitterAdapter
from .automation_adapter import AutomationAdapter, PipelineTask, PipelineResult

__all__ = [
    "BaseAdapter",
    "Content", 
    "ContentType",
    "PublishResult",
    "Analytics",
    "YouTubeAdapter",
    "TwitterAdapter",
    "AutomationAdapter",
    "PipelineTask",
    "PipelineResult",
    "ADAPTER_REGISTRY",
    "get_adapter",
    "list_adapters",
]

ADAPTER_REGISTRY: dict[str, Type[BaseAdapter]] = {
    "youtube": YouTubeAdapter,
    "twitter": TwitterAdapter,
}


def get_adapter(platform: str, config: dict) -> BaseAdapter:
    """Factory function to get adapter instance.
    
    Args:
        platform: Platform name (e.g., "youtube", "twitter")
        config: Platform-specific configuration
        
    Returns:
        Configured adapter instance
        
    Raises:
        ValueError: If platform is not registered
    """
    if platform not in ADAPTER_REGISTRY:
        raise ValueError(f"Unknown platform: {platform}. Available: {list_adapters()}")
    return ADAPTER_REGISTRY[platform](config)


def list_adapters() -> list[str]:
    """List all available adapter platforms."""
    return list(ADAPTER_REGISTRY.keys())
