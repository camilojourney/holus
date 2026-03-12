"""Base class for all platform framers.

A framer takes a :class:`~holus.agents.content_factory.models.ContentPiece`
(with raw_content from a specialist) and produces a
:class:`~holus.agents.content_factory.models.PlatformAdaptation` for one
specific platform.

Each framer enforces its platform's character limits, tone, and format rules.
Framers that cannot produce output for a given format return ``None`` — the
pipeline filters these out.
"""

from __future__ import annotations

import abc
import json
import logging
from typing import Any

from ..models import ContentPiece, PlatformAdaptation, PlatformType

logger = logging.getLogger(__name__)


class BasePlatformFramer(abc.ABC):
    """Abstract base for all platform framers.

    Subclasses must:
    - Set ``platform`` as a class variable.
    - Set ``char_limit`` as a class variable.
    - Implement ``frame``.
    """

    platform: PlatformType
    char_limit: int

    @abc.abstractmethod
    async def frame(
        self,
        piece: ContentPiece,
        context: dict[str, Any],
    ) -> PlatformAdaptation | None:
        """Adapt a content piece for this platform.

        Args:
            piece: The :class:`ContentPiece` with raw specialist output.
            context: May contain ``claude_client``, ``brand``, ``platform_knowledge``.

        Returns:
            A :class:`PlatformAdaptation` if this format x platform combination
            is supported, or ``None`` if it should be skipped.
        """

    def _truncate(self, text: str, limit: int | None = None) -> str:
        """Hard-truncate text to char_limit (or custom limit), adding ellipsis."""
        cap = limit or self.char_limit
        if len(text) <= cap:
            return text
        return text[: cap - 1] + "…"

    def _extract_raw(self, piece: ContentPiece) -> dict[str, Any]:
        """Parse raw_content JSON from a piece; return empty dict on error."""
        try:
            payload = json.loads(piece.raw_content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse raw_content for piece %s", piece.piece_id)
            return {}
        return payload if isinstance(payload, dict) else {}

    def _make_adaptation(
        self,
        adapted_content: str,
        media_urls: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        scheduling_suggestion: str = "",
        language: str = "en",
    ) -> PlatformAdaptation:
        """Build a :class:`PlatformAdaptation` for this framer's platform."""
        resolved_metadata = metadata.copy() if metadata else {}
        if scheduling_suggestion:
            resolved_metadata["scheduling_suggestion"] = scheduling_suggestion
        if language:
            resolved_metadata["language"] = language
        return PlatformAdaptation(
            platform=self.platform,
            adapted_content=adapted_content,
            media_urls=media_urls or [],
            metadata=resolved_metadata,
            char_count=len(adapted_content),
        )
