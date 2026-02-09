"""
Video Publisher — Publishes video content to all enabled video platforms.

Uses platform adapters (YouTube, TikTok, etc.) for the actual API calls.
SPEC-002: Content Strategy Domain / SPEC-003: Adapter System.
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from agents.content_strategy.adapters.base_adapter import (
    BaseAdapter,
    Content,
    ContentType,
    PublishResult,
)


class VideoPublisher:
    """
    Publishes video content to enabled video platforms.

    Responsibilities:
    - Load and manage video-capable adapters
    - Validate content before publishing
    - Publish to all enabled platforms in parallel
    - Collect and return results
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.adapters: dict[str, BaseAdapter] = {}
        self._load_adapters()
        logger.info(
            f"VideoPublisher initialized with {len(self.adapters)} adapters: "
            f"{list(self.adapters.keys())}"
        )

    def _load_adapters(self) -> None:
        """Load adapters for enabled video platforms from config."""
        platforms = self.config.get("platforms", {})

        # Lazy import to avoid circular imports
        from agents.content_strategy.adapters.youtube_adapter import YouTubeAdapter

        adapter_map: dict[str, type[BaseAdapter]] = {
            "youtube": YouTubeAdapter,
            # "tiktok": TikTokAdapter,  # TODO: Implement
        }

        for platform_name, platform_config in platforms.items():
            if not platform_config.get("enabled", True):
                continue
            adapter_cls = adapter_map.get(platform_name)
            if adapter_cls is None:
                logger.warning(f"No adapter for video platform: {platform_name}")
                continue
            try:
                self.adapters[platform_name] = adapter_cls(platform_config)
            except Exception as e:
                logger.error(f"Failed to load {platform_name} adapter: {e}")

    async def publish(self, content: Content) -> dict[str, PublishResult]:
        """Publish video content to all enabled platforms.

        Args:
            content: The content to publish (must be VIDEO type).

        Returns:
            Dict mapping platform name to PublishResult.
        """
        if content.type != ContentType.VIDEO:
            return {
                name: PublishResult(
                    success=False,
                    platform=name,
                    error=f"Expected VIDEO content, got {content.type}",
                )
                for name in self.adapters
            }

        results: dict[str, PublishResult] = {}

        for name, adapter in self.adapters.items():
            try:
                # Validate first
                valid, errors = adapter.validate_content(content)
                if not valid:
                    results[name] = PublishResult(
                        success=False,
                        platform=name,
                        error="; ".join(errors),
                    )
                    continue

                # Adapt and publish
                adapted = adapter.adapt_content(content)
                result = await adapter.publish(adapted)
                results[name] = result

            except NotImplementedError:
                results[name] = PublishResult(
                    success=False,
                    platform=name,
                    error="Adapter not yet implemented",
                )
            except Exception as e:
                logger.error(f"Failed to publish to {name}: {e}")
                results[name] = PublishResult(
                    success=False,
                    platform=name,
                    error=str(e),
                )

        successful = sum(1 for r in results.values() if r.success)
        logger.info(
            f"Published video to {successful}/{len(results)} platforms"
        )
        return results
