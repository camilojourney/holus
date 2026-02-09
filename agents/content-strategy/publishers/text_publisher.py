"""
Text Publisher — Publishes text content to all enabled text platforms.

Uses platform adapters (Twitter, LinkedIn, etc.) for the actual API calls.
SPEC-002: Content Strategy Domain / SPEC-003: Adapter System.
"""
from __future__ import annotations

from loguru import logger

from agents.content_strategy.adapters.base_adapter import (
    BaseAdapter,
    Content,
    ContentType,
    PublishResult,
)


class TextPublisher:
    """
    Publishes text content to enabled text platforms.

    Responsibilities:
    - Load and manage text-capable adapters (Twitter, LinkedIn, etc.)
    - Validate content before publishing
    - Publish to all enabled platforms
    - Collect and return results
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.adapters: dict[str, BaseAdapter] = {}
        self._load_adapters()
        logger.info(
            f"TextPublisher initialized with {len(self.adapters)} adapters: "
            f"{list(self.adapters.keys())}"
        )

    def _load_adapters(self) -> None:
        """Load adapters for enabled text platforms from config."""
        platforms = self.config.get("platforms", {})

        from agents.content_strategy.adapters.twitter_adapter import TwitterAdapter

        adapter_map: dict[str, type[BaseAdapter]] = {
            "twitter": TwitterAdapter,
            # "linkedin": LinkedInAdapter,  # TODO: Implement
        }

        for platform_name, platform_config in platforms.items():
            if not platform_config.get("enabled", True):
                continue
            adapter_cls = adapter_map.get(platform_name)
            if adapter_cls is None:
                logger.warning(f"No adapter for text platform: {platform_name}")
                continue
            try:
                self.adapters[platform_name] = adapter_cls(platform_config)
            except Exception as e:
                logger.error(f"Failed to load {platform_name} adapter: {e}")

    async def publish(self, content: Content) -> dict[str, PublishResult]:
        """Publish text content to all enabled platforms.

        Args:
            content: The content to publish.

        Returns:
            Dict mapping platform name to PublishResult.
        """
        results: dict[str, PublishResult] = {}

        for name, adapter in self.adapters.items():
            if content.type not in adapter.content_types:
                results[name] = PublishResult(
                    success=False,
                    platform=name,
                    error=f"Content type {content.type} not supported by {name}",
                )
                continue

            try:
                valid, errors = adapter.validate_content(content)
                if not valid:
                    results[name] = PublishResult(
                        success=False,
                        platform=name,
                        error="; ".join(errors),
                    )
                    continue

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
            f"Published text to {successful}/{len(results)} platforms"
        )
        return results
