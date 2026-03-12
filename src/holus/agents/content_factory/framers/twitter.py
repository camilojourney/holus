"""Twitter/X framer.

Twitter/X character limit: 280 per tweet.

Format support:
- text       → condensed single tweet or 3-5 tweet thread
- diagram    → inline image + short caption (≤280)
- video_brief → video post + short caption
- carousel   → skip (no native carousel; would be a thread of images)
- pdf        → link + hook tweet (≤280)
"""

from __future__ import annotations

from typing import Any

from ..models import ContentPiece, FormatType, PlatformAdaptation, PlatformType
from .base import BasePlatformFramer

_TWEET_LIMIT = 280


class TwitterFramer(BasePlatformFramer):
    """Frames content for Twitter/X."""

    platform = PlatformType.TWITTER
    char_limit = _TWEET_LIMIT

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
        elif fmt == FormatType.VIDEO_BRIEF:
            return self._frame_video_brief(raw)
        elif fmt == FormatType.PDF:
            return self._frame_pdf(raw)
        # carousel → skip on Twitter
        return None

    def _frame_text(self, raw: dict[str, Any]) -> PlatformAdaptation:
        text = raw.get("text", "")
        hook = raw.get("hook", "")

        # Use hook as tweet if it fits; otherwise condense the full text
        tweet = hook or text
        tweet = self._truncate(tweet, _TWEET_LIMIT)

        is_thread = len(text) > _TWEET_LIMIT
        return self._make_adaptation(
            adapted_content=tweet,
            metadata={"format": "text", "is_thread": is_thread},
            scheduling_suggestion="Weekdays 8-10am or 12-1pm EST",
        )

    def _frame_diagram(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        explanation = raw.get("explanation", "")
        caption = title or explanation
        caption = self._truncate(caption, _TWEET_LIMIT)
        return self._make_adaptation(
            adapted_content=caption,
            media_urls=["diagram_image"],
            metadata={"format": "diagram"},
        )

    def _frame_video_brief(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        caption = self._truncate(title, _TWEET_LIMIT)
        return self._make_adaptation(
            adapted_content=caption,
            media_urls=["video"],
            metadata={"format": "video_brief"},
        )

    def _frame_pdf(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_takeaway = raw.get("key_takeaway", "")
        hook = key_takeaway or title
        tweet = self._truncate(hook, _TWEET_LIMIT - 25)  # leave room for link
        return self._make_adaptation(
            adapted_content=tweet,
            media_urls=["pdf_link"],
            metadata={"format": "pdf"},
        )
