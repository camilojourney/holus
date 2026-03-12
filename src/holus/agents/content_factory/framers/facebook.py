"""Facebook framer.

Facebook character limit: 63,206 — effectively unlimited for our use case.

Format support (all five):
- text       → full post, shareable, conversational
- carousel   → text summary of slides (Facebook doesn't support PDF carousels)
- pdf        → link + summary
- diagram    → inline image + explanation
- video_brief → video post + caption

Facebook has a bilingual routing marker: if context contains
``language: "es"``, the post gets a Spanish marker for the @camilojourney
account. The distribution layer handles the actual routing.
"""

from __future__ import annotations

from typing import Any

from ..models import ContentPiece, FormatType, PlatformAdaptation, PlatformType
from .base import BasePlatformFramer


class FacebookFramer(BasePlatformFramer):
    """Frames content for Facebook."""

    platform = PlatformType.FACEBOOK
    char_limit = 63_206

    async def frame(
        self,
        piece: ContentPiece,
        context: dict[str, Any],
    ) -> PlatformAdaptation | None:
        raw = self._extract_raw(piece)
        fmt = piece.format
        language = context.get("language", "en")

        if fmt == FormatType.TEXT:
            return self._frame_text(raw, language)
        elif fmt == FormatType.CAROUSEL:
            return self._frame_carousel(raw, language)
        elif fmt == FormatType.PDF:
            return self._frame_pdf(raw, language)
        elif fmt == FormatType.DIAGRAM:
            return self._frame_diagram(raw, language)
        elif fmt == FormatType.VIDEO_BRIEF:
            return self._frame_video_brief(raw, language)
        return None

    def _frame_text(self, raw: dict[str, Any], language: str) -> PlatformAdaptation:
        text = raw.get("text", "")
        return self._make_adaptation(
            adapted_content=text,
            metadata={"format": "text", "language_routing": language},
            language=language,
        )

    def _frame_carousel(self, raw: dict[str, Any], language: str) -> PlatformAdaptation:
        slides = raw.get("slides", [])
        summary = raw.get("topic_summary", "")
        slide_texts = "\n".join(
            f"{s.get('slide_number', i + 1)}. {s.get('headline', '')}" for i, s in enumerate(slides)
        )
        body = f"{summary}\n\n{slide_texts}" if slide_texts else summary
        return self._make_adaptation(
            adapted_content=body,
            metadata={
                "format": "carousel",
                "slide_count": len(slides),
                "language_routing": language,
            },
            language=language,
        )

    def _frame_pdf(self, raw: dict[str, Any], language: str) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_takeaway = raw.get("key_takeaway", "")
        body = f"{title}\n\n{key_takeaway}" if key_takeaway else title
        return self._make_adaptation(
            adapted_content=body,
            media_urls=["pdf_link"],
            metadata={"format": "pdf", "language_routing": language},
            language=language,
        )

    def _frame_diagram(self, raw: dict[str, Any], language: str) -> PlatformAdaptation:
        title = raw.get("title", "")
        explanation = raw.get("explanation", "")
        body = f"{title}\n\n{explanation}" if explanation else title
        return self._make_adaptation(
            adapted_content=body,
            media_urls=["diagram_image"],
            metadata={"format": "diagram", "language_routing": language},
            language=language,
        )

    def _frame_video_brief(self, raw: dict[str, Any], language: str) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_points = raw.get("key_points", [])
        points_text = "\n".join(f"• {p}" for p in key_points[:5])
        body = f"{title}\n\n{points_text}" if points_text else title
        return self._make_adaptation(
            adapted_content=body,
            media_urls=["video"],
            metadata={"format": "video_brief", "language_routing": language},
            language=language,
        )
