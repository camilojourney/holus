"""Text Publisher — Publishes text content via platform adapters.

Uses the adapter pattern (SPEC-003) to validate, adapt, and push
text content to Twitter, LinkedIn, and other text platforms.
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


class TextPublisher:
    """Publishes text content through registered text-capable adapters.

    Usage:
        publisher = TextPublisher(config)
        publisher.register_adapter(TwitterAdapter(tw_config))
        results = await publisher.publish(content)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._adapters: dict[str, BaseAdapter] = {}
        logger.info("TextPublisher initialized")

    def register_adapter(self, adapter: BaseAdapter) -> None:
        """Register a platform adapter for text publishing."""
        if ContentType.TEXT not in adapter.content_types:
            logger.warning(
                f"Adapter '{adapter.platform}' doesn't support TEXT, skipping"
            )
            return
        self._adapters[adapter.platform] = adapter
        logger.info(f"Registered text adapter: {adapter.platform}")

    @property
    def platforms(self) -> list[str]:
        """List of registered platform names."""
        return list(self._adapters.keys())

    def validate(self, content: Content) -> dict[str, tuple[bool, list[str]]]:
        """Validate content against all registered adapters."""
        results = {}
        for name, adapter in self._adapters.items():
            results[name] = adapter.validate_content(content)
        return results

    async def publish(
        self,
        content: Content,
        platforms: list[str] | None = None,
    ) -> list[PublishResult]:
        """Publish text content to one or more platforms.

        Args:
            content: The text content to publish.
            platforms: Subset of platforms to target (all if None).

        Returns:
            List of PublishResult objects, one per platform.
        """
        if content.type != ContentType.TEXT:
            return [
                PublishResult(
                    success=False,
                    platform="all",
                    error=f"TextPublisher only handles TEXT, got {content.type}",
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

                adapted = adapter.adapt_content(content)
                adapted = await adapter.pre_publish(adapted)
                result = await adapter.publish(adapted)
                results.append(result)
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
