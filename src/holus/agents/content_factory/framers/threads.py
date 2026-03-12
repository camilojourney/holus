"""Threads framer.

Threads character limit: 500 per post.

Format support:
- text       → conversational, no hashtags, often ends with a question
- diagram    → text description (no image upload support yet)
- pdf        → skip (no link posts — no URL preview)
- carousel   → skip (no carousel support)
- video_brief → skip (video support limited; skip for now)
"""

from __future__ import annotations

from typing import Any

from ..models import ContentPiece, FormatType, PlatformAdaptation, PlatformType
from .base import BasePlatformFramer


class ThreadsFramer(BasePlatformFramer):
    """Frames content for Threads."""

    platform = PlatformType.THREADS
    char_limit = 500

    async def frame(
        self,
        piece: ContentPiece,
        context: dict[str, Any],
    ) -> PlatformAdaptation | None:
        raw = self._extract_raw(piece)
        fmt = piece.format

        if fmt == FormatType.TEXT:
            return self._frame_text(raw)
        elif fmt == FormatType.DIAGRAM:
            return self._frame_diagram(raw)
        # carousel, pdf, video_brief → skip on Threads
        return None

    def _frame_text(self, raw: dict[str, Any]) -> PlatformAdaptation:
        hook = raw.get("hook", "")
        text = raw.get("text", "")

        # Threads: conversational, no hashtags, question-ending preferred
        body = hook or text
        body = self._truncate(body, self.char_limit)

        # If the post doesn't end with a question mark, try to append one
        if body and not body.rstrip().endswith("?"):
            question = "\n\nWhat do you think?"
            if len(body) + len(question) <= self.char_limit:
                body = body + question

        return self._make_adaptation(
            adapted_content=body,
            metadata={"format": "text"},
            scheduling_suggestion="Weekdays 9am-12pm EST",
        )

    def _frame_diagram(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        explanation = raw.get("explanation", "")
        # No image support on Threads — use text description only
        body = f"{title}\n\n{explanation}" if explanation else title
        body = self._truncate(body, self.char_limit)
        return self._make_adaptation(
            adapted_content=body,
            metadata={"format": "diagram", "media_skipped": True},
        )
