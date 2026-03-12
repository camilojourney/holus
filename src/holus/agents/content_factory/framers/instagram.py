"""Instagram framer.

Instagram character limit: 2200.
Instagram requires media — text-only posts are blocked.

Format support:
- carousel   → multi-image post + caption (hook first, 10-15 hashtags)
- diagram    → single image + caption
- video_brief → Reel + caption
- text       → caption only with required media placeholder
- pdf        → skip (no PDF support on Instagram)
"""

from __future__ import annotations

from typing import Any

from ..models import ContentPiece, FormatType, PlatformAdaptation, PlatformType
from .base import BasePlatformFramer

_MAX_HASHTAGS = 15


class InstagramFramer(BasePlatformFramer):
    """Frames content for Instagram."""

    platform = PlatformType.INSTAGRAM
    char_limit = 2200

    async def frame(
        self,
        piece: ContentPiece,
        context: dict[str, Any],
    ) -> PlatformAdaptation | None:
        raw = self._extract_raw(piece)
        fmt = piece.format

        if fmt == FormatType.CAROUSEL:
            return self._frame_carousel(raw)
        elif fmt == FormatType.DIAGRAM:
            return self._frame_diagram(raw)
        elif fmt == FormatType.VIDEO_BRIEF:
            return self._frame_video_brief(raw)
        elif fmt == FormatType.TEXT:
            return self._frame_text(raw)
        # pdf → skip
        return None

    def _frame_text(self, raw: dict[str, Any]) -> PlatformAdaptation:
        hook = raw.get("hook", "")
        text = raw.get("text", "")
        hashtags = raw.get("hashtags", [])

        caption = hook or text
        if hashtags:
            tag_str = " ".join(f"#{h}" for h in hashtags[:_MAX_HASHTAGS])
            candidate = f"{caption}\n.\n.\n.\n{tag_str}"
            caption = candidate if len(candidate) <= self.char_limit else self._truncate(caption)
        else:
            caption = self._truncate(caption)

        return self._make_adaptation(
            adapted_content=caption,
            media_urls=["image_required"],  # Instagram requires media
            metadata={"format": "text", "hashtag_count": len(hashtags)},
            scheduling_suggestion="Weekdays 11am-1pm or 7-9pm EST",
        )

    def _frame_carousel(self, raw: dict[str, Any]) -> PlatformAdaptation:
        slides = raw.get("slides", [])
        summary = raw.get("topic_summary", "")

        first_slide = slides[0] if slides else {}
        hook = first_slide.get("headline", summary or "Swipe →")
        slide_count = len(slides)

        caption = f"{hook}\n\nSwipe to see all {slide_count} slides 👉"
        caption = self._truncate(caption)

        return self._make_adaptation(
            adapted_content=caption,
            media_urls=[f"slide_{i + 1}" for i in range(slide_count)],
            metadata={"format": "carousel", "slide_count": slide_count},
            scheduling_suggestion="Weekdays 11am or 7pm EST",
        )

    def _frame_diagram(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        explanation = raw.get("explanation", "")
        caption = f"{title}\n\n{explanation}" if explanation else title
        caption = self._truncate(caption)
        return self._make_adaptation(
            adapted_content=caption,
            media_urls=["diagram_image"],
            metadata={"format": "diagram"},
        )

    def _frame_video_brief(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_points = raw.get("key_points", [])
        points_text = "\n".join(f"✅ {p}" for p in key_points[:3])
        caption = f"{title}\n\n{points_text}" if points_text else title
        caption = self._truncate(caption)
        return self._make_adaptation(
            adapted_content=caption,
            media_urls=["reel_video"],
            metadata={"format": "video_brief"},
            scheduling_suggestion="Tue-Fri 11am or 8pm EST",
        )
