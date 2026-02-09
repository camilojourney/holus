"""Video Publisher — Publishes video content via platform adapters.

Uses the adapter pattern (SPEC-003) to validate, adapt, and push
video content to YouTube, TikTok, and other video platforms.
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from ..adapters.base_adapter import (
    BaseAdapter,
    Content,
    ContentType,
    PublishResult,
)


class VideoPublisher:
    """Publishes video content through registered video-capable adapters.

    Usage:
        publisher = VideoPublisher(config)
        publisher.register_adapter(YouTubeAdapter(yt_config))
        results = await publisher.publish(content)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._adapters: dict[str, BaseAdapter] = {}
        logger.info("VideoPublisher initialized")

    def register_adapter(self, adapter: BaseAdapter) -> None:
        """Register a platform adapter for video publishing."""
        if ContentType.VIDEO not in adapter.content_types:
            logger.warning(
                f"Adapter '{adapter.platform}' doesn't support VIDEO, skipping"
            )
            return
        self._adapters[adapter.platform] = adapter
        logger.info(f"Registered video adapter: {adapter.platform}")

    @property
    def platforms(self) -> list[str]:
        """List of registered platform names."""
        return list(self._adapters.keys())

    def validate(self, content: Content) -> dict[str, tuple[bool, list[str]]]:
        """Validate content against all registered adapters.

        Returns:
            Dict mapping platform name to (valid, errors) tuples.
        """
        results = {}
        for name, adapter in self._adapters.items():
            results[name] = adapter.validate_content(content)
        return results

    async def publish(
        self,
        content: Content,
        platforms: list[str] | None = None,
    ) -> list[PublishResult]:
        """Publish video content to one or more platforms.

        Args:
            content: The video content to publish.
            platforms: Subset of platforms to target (all if None).

        Returns:
            List of PublishResult objects, one per platform.
        """
        if content.type != ContentType.VIDEO:
            return [
                PublishResult(
                    success=False,
                    platform="all",
                    error=f"VideoPublisher only handles VIDEO, got {content.type}",
                )
            ]

        targets = self._adapters
        if platforms:
            targets = {k: v for k, v in self._adapters.items() if k in platforms}

        if not targets:
            return [
                PublishResult(
                    success=False,
                    platform="none",
                    error="No matching adapters registered",
                )
            ]

        results: list[PublishResult] = []
        for name, adapter in targets.items():
            try:
                # Validate
                valid, errors = adapter.validate_content(content)
                if not valid:
                    results.append(
                        PublishResult(
                            success=False,
                            platform=name,
                            error="; ".join(errors),
                        )
                    )
                    continue

                # Adapt content for platform
                adapted = adapter.adapt_content(content)

                # Pre-publish hook
                adapted = await adapter.pre_publish(adapted)

                # Publish
                result = await adapter.publish(adapted)
                results.append(result)

                # Post-publish hook
                await adapter.post_publish(result)

            except NotImplementedError:
                results.append(
                    PublishResult(
                        success=False,
                        platform=name,
                        error=f"{name} publishing not yet implemented",
                    )
                )
            except Exception as e:
                logger.error(f"Failed to publish to {name}: {e}")
                results.append(
                    PublishResult(success=False, platform=name, error=str(e))
                )

        return results
