"""LinkedIn framer.

LinkedIn supports all five formats:
- carousel  → mentions PDF upload + slide count
- pdf       → link + executive summary
- diagram   → inline image + explanation
- video_brief → passes to genpeli for video post
- text      → full post (≤3000 chars), professional tone

Best posting times: Tue-Thu 7-9am, 12-1pm (EST).
"""

from __future__ import annotations

from typing import Any

from ..models import ContentPiece, FormatType, PlatformAdaptation, PlatformType
from .base import BasePlatformFramer


class LinkedInFramer(BasePlatformFramer):
    """Frames content for LinkedIn."""

    platform = PlatformType.LINKEDIN
    char_limit = 3000

    async def frame(
        self,
        piece: ContentPiece,
        context: dict[str, Any],
    ) -> PlatformAdaptation | None:
        """Adapt content for LinkedIn.

        All formats are supported. Returns a PlatformAdaptation with
        format-specific metadata.
        """
        raw = self._extract_raw(piece)
        fmt = piece.format

        if fmt == FormatType.TEXT:
            return self._frame_text(raw)
        elif fmt == FormatType.CAROUSEL:
            return self._frame_carousel(raw)
        elif fmt == FormatType.PDF:
            return self._frame_pdf(raw)
        elif fmt == FormatType.DIAGRAM:
            return self._frame_diagram(raw)
        elif fmt == FormatType.VIDEO_BRIEF:
            return self._frame_video_brief(raw)
        return None

    def _frame_text(self, raw: dict[str, Any]) -> PlatformAdaptation:
        text = raw.get("text", "")
        hook = raw.get("hook", "")
        hashtags = raw.get("hashtags", [])

        body = text or hook or "Content not available."
        if hashtags:
            tag_str = " ".join(f"#{h}" for h in hashtags[:5])
            candidate = f"{body}\n\n{tag_str}"
            body = candidate if len(candidate) <= self.char_limit else self._truncate(body)

        return self._make_adaptation(
            adapted_content=self._truncate(body),
            metadata={"hashtags": hashtags, "format": "text"},
            scheduling_suggestion="Tue-Thu 7-9am or 12-1pm EST",
        )

    def _frame_carousel(self, raw: dict[str, Any]) -> PlatformAdaptation:
        slides = raw.get("slides", [])
        cta = raw.get("cta_slide", {})
        summary = raw.get("topic_summary", "")

        slide_count = len(slides) + (1 if cta else 0)
        teaser = f"{summary}\n\n→ Swipe through {slide_count} slides to learn more."
        return self._make_adaptation(
            adapted_content=self._truncate(teaser),
            media_urls=["carousel_pdf"],  # placeholder — pipeline fills real URL
            metadata={"slide_count": slide_count, "format": "carousel"},
            scheduling_suggestion="Tue-Thu 8am EST for max reach",
        )

    def _frame_pdf(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_takeaway = raw.get("key_takeaway", "")
        sections = raw.get("sections", [])

        lines = []
        if title:
            lines.append(f"📄 {title}")
        if key_takeaway:
            lines.append(f"\n{key_takeaway}")
        if sections:
            lines.append(f"\nInside ({len(sections)} sections):")
            for s in sections[:3]:
                heading = s.get("heading", "")
                if heading:
                    lines.append(f"  • {heading}")
        lines.append("\n👇 Full guide below")
        body = "\n".join(lines)

        return self._make_adaptation(
            adapted_content=self._truncate(body),
            media_urls=["pdf_document"],  # placeholder
            metadata={"format": "pdf", "section_count": len(sections)},
            scheduling_suggestion="Mon or Wed morning EST",
        )

    def _frame_diagram(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        explanation = raw.get("explanation", "")
        diagram_type = raw.get("diagram_type", "diagram")

        body = f"{title}\n\n{explanation}" if explanation else title
        body = self._truncate(body)

        return self._make_adaptation(
            adapted_content=body,
            media_urls=["diagram_image"],  # placeholder
            metadata={"diagram_type": diagram_type, "format": "diagram"},
            scheduling_suggestion="Wed-Thu 8am EST",
        )

    def _frame_video_brief(self, raw: dict[str, Any]) -> PlatformAdaptation:
        title = raw.get("title", "")
        key_points = raw.get("key_points", [])
        tone = raw.get("tone", "")

        points_text = "\n".join(f"• {p}" for p in key_points[:5])
        body = f"{title}\n\n{points_text}" if points_text else title
        body = self._truncate(body)

        return self._make_adaptation(
            adapted_content=body,
            media_urls=["video"],  # placeholder — genpeli fills real URL
            metadata={"format": "video_brief", "tone": tone},
            scheduling_suggestion="Tue-Thu 7am or 5pm EST",
        )
