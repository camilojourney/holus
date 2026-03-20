"""Infographic renderer — generates animated frames from structured layout data.

Uses Pillow (PIL) for all drawing. Reads brand colors and typography from
BrandVisualIdentity. Items are drawn as colored rounded rectangles with
text labels (real SVG icons can be added later).

Usage::

    from holus.agents.marketing.models import BrandVisualIdentity
    from holus.visual.infographic import InfographicRenderer
    from holus.visual.infographic_layout import InfographicLayout

    renderer = InfographicRenderer(BrandVisualIdentity())
    layout = InfographicLayout(title="AI Stack", rows=[...])
    layout.compute_positions()
    frames = renderer.render(layout)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from holus.visual.icon_registry import IconRegistry

if TYPE_CHECKING:
    from holus.agents.marketing.models import BrandVisualIdentity
    from holus.visual.infographic_layout import InfographicItem, InfographicLayout, InfographicRow

logger = logging.getLogger(__name__)


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert a hex color string to an RGBA tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, falling back to Pillow's default."""
    try:
        return ImageFont.truetype(name, size)
    except (OSError, IOError):
        # Try common system paths
        for path in (
            f"/System/Library/Fonts/{name}.ttc",
            f"/System/Library/Fonts/Supplemental/{name}.ttf",
            f"/usr/share/fonts/truetype/{name.lower()}/{name}.ttf",
        ):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()


class InfographicRenderer:
    """Renders animated infographic frames from an InfographicLayout.

    Each frame is a PIL Image in RGBA mode. The renderer uses brand config
    for colors and typography.
    """

    def __init__(self, brand_config: BrandVisualIdentity) -> None:
        self.brand = brand_config
        self.icon_registry = IconRegistry()

        # Load fonts from brand config
        primary_font = brand_config.typography.primary_font
        sizes = brand_config.typography.sizes

        self._title_font = _load_font(primary_font, sizes.get("headline", 48))
        self._subtitle_font = _load_font(primary_font, sizes.get("subheadline", 32))
        self._category_font = _load_font(primary_font, sizes.get("body", 18))
        self._item_font = _load_font(primary_font, max(12, sizes.get("caption", 14)))

    def render(self, layout: InfographicLayout) -> list[Image.Image]:
        """Generate all PIL frames for the animation.

        Args:
            layout: The infographic layout with positions already computed
                (call ``layout.compute_positions()`` first).

        Returns:
            List of RGBA PIL Images, one per frame.
        """
        total_frames = int(layout.duration_sec * layout.fps)
        frames: list[Image.Image] = []

        for frame_idx in range(total_frames):
            t = frame_idx / max(total_frames - 1, 1)
            frame = self._draw_frame(layout, t)
            frames.append(frame)

        logger.info(
            "Rendered %d frames at %dx%d for '%s'",
            len(frames), layout.width, layout.height, layout.title,
        )
        return frames

    def _draw_frame(self, layout: InfographicLayout, t: float) -> Image.Image:
        """Draw a single frame at normalized time t (0.0 to 1.0)."""
        img = Image.new("RGBA", (layout.width, layout.height), _hex_to_rgba(layout.background_color))
        draw = ImageDraw.Draw(img)

        # Draw title and subtitle (always visible with fade-in at start)
        title_alpha = min(1.0, t / 0.08) if t < 0.08 else 1.0
        self._draw_title(draw, layout, title_alpha)

        # Draw category labels and items for each row
        title_area_height = 160
        margin = 40
        gap = 16
        num_rows = len(layout.rows)
        content_height = layout.height - title_area_height - margin
        row_height = min(140, (content_height - gap * (num_rows - 1)) / max(num_rows, 1))

        for row_idx, row in enumerate(layout.rows):
            y_pos = title_area_height + row_idx * (row_height + gap)
            # Category label appears when the first item in the row appears
            first_appear = min((item.appear_at for item in row.items), default=0.0)
            cat_alpha = self._fade_alpha(t, first_appear)
            if cat_alpha > 0:
                self._draw_category_label(draw, row, y_pos, row_height, cat_alpha)

            for item in row.items:
                alpha = self._fade_alpha(t, item.appear_at)
                if alpha > 0:
                    self._draw_item(draw, item, alpha)

        return img

    def _fade_alpha(self, t: float, appear_at: float) -> float:
        """Compute fade-in alpha for an element.

        Fade-in takes ~50ms equivalent in normalized time, which at 10fps/8sec
        is approximately 0.00625. We use 0.05 for a visible transition.
        """
        if t < appear_at:
            return 0.0
        fade_duration = 0.05
        if t >= appear_at + fade_duration:
            return 1.0
        return (t - appear_at) / fade_duration

    def _draw_title(self, draw: ImageDraw.ImageDraw, layout: InfographicLayout, alpha: float) -> None:
        """Draw the title and subtitle centered at the top."""
        if alpha <= 0:
            return

        a = int(alpha * 255)
        text_color = _hex_to_rgba(self.brand.colors.text if self.brand.colors.text != layout.background_color else "#FFFFFF", a)

        # For dark backgrounds, use white text; for light backgrounds, use brand text color
        bg_brightness = sum(_hex_to_rgba(layout.background_color)[:3]) / 3
        if bg_brightness < 128:
            text_color = (255, 255, 255, a)

        # Title
        draw.text(
            (layout.width / 2, 50),
            layout.title,
            fill=text_color,
            font=self._title_font,
            anchor="mt",
        )

        # Subtitle
        if layout.subtitle:
            muted_color = (*text_color[:3], int(alpha * 180))
            draw.text(
                (layout.width / 2, 110),
                layout.subtitle,
                fill=muted_color,
                font=self._subtitle_font,
                anchor="mt",
            )

    def _draw_category_label(
        self,
        draw: ImageDraw.ImageDraw,
        row: InfographicRow,
        y_pos: float,
        row_height: float,
        alpha: float,
    ) -> None:
        """Draw a category label on the left side of a row."""
        if alpha <= 0:
            return

        a = int(alpha * 255)
        # Use accent color for category labels
        label_color = _hex_to_rgba(self.brand.colors.accent, a)

        # Draw category text vertically centered in the row
        draw.text(
            (30, y_pos + row_height / 2),
            row.category,
            fill=label_color,
            font=self._category_font,
            anchor="lm",
        )

    def _draw_item(self, draw: ImageDraw.ImageDraw, item: InfographicItem, alpha: float) -> None:
        """Draw a single item as a colored rounded rectangle with text label."""
        if alpha <= 0:
            return

        a = int(alpha * 255)
        display_name, hex_color = self.icon_registry.get_icon(item.icon)

        x, y = item.position
        w, h = item.size

        # Draw rounded rectangle background
        icon_bg = _hex_to_rgba(hex_color, a)
        radius = min(12, int(min(w, h) * 0.1))
        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=radius,
            fill=icon_bg,
        )

        # Draw item name as text centered in the rectangle
        # Use white text on colored backgrounds
        text_color = (255, 255, 255, a)
        # Center the display name
        draw.text(
            (x + w / 2, y + h / 2 - 8),
            display_name,
            fill=text_color,
            font=self._item_font,
            anchor="mm",
        )
        # Draw the item name (may differ from icon display name) below
        if item.name != display_name:
            small_color = (255, 255, 255, int(alpha * 200))
            draw.text(
                (x + w / 2, y + h / 2 + 12),
                item.name,
                fill=small_color,
                font=self._item_font,
                anchor="mm",
            )
