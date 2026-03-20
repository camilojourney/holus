"""Pydantic models for infographic layout and animation timing.

Describes the structured data that drives infographic rendering:
rows of categorized items, layout style, animation type, and dimensions.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LayoutStyle(StrEnum):
    """Layout arrangement for infographic items."""

    GRID = "grid"
    COMPARISON = "comparison"
    FLOW = "flow"
    TIMELINE = "timeline"


class AnimationType(StrEnum):
    """Animation sequence for item appearance."""

    SEQUENTIAL = "sequential"
    ROW_BY_ROW = "row-by-row"
    FADE_ALL = "fade-all"
    BUILD_UP = "build-up"


class InfographicItem(BaseModel):
    """A single item (icon cell) in the infographic."""

    name: str = Field(description="Display name for the item")
    icon: str = Field(description="Icon registry key (e.g. 'claude', 'python')")
    appear_at: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Normalized time when item appears (0-1)"
    )
    position: tuple[float, float] = Field(
        default=(0.0, 0.0), description="(x, y) position in pixels"
    )
    size: tuple[float, float] = Field(
        default=(120.0, 120.0), description="(width, height) in pixels"
    )


class InfographicRow(BaseModel):
    """A row of items grouped by category."""

    category: str = Field(description="Category label (e.g. 'Foundation Models')")
    items: list[InfographicItem] = Field(
        default_factory=list, description="Items in this row"
    )


class InfographicLayout(BaseModel):
    """Complete infographic layout specification.

    Create the layout with rows and items, then call ``compute_positions()``
    to calculate pixel positions and animation timing for each item.
    """

    title: str = Field(description="Main title text")
    subtitle: str = Field(default="", description="Subtitle text")
    rows: list[InfographicRow] = Field(
        default_factory=list, description="Rows of categorized items"
    )
    style: LayoutStyle = Field(
        default=LayoutStyle.GRID, description="Layout arrangement"
    )
    animation: AnimationType = Field(
        default=AnimationType.SEQUENTIAL, description="Animation sequence"
    )
    background_color: str = Field(
        default="#1A1A2E", description="Background hex color"
    )
    fps: int = Field(default=10, ge=1, le=30, description="Frames per second")
    duration_sec: int = Field(
        default=8, ge=1, le=40, description="Animation duration in seconds"
    )
    width: int = Field(default=1080, ge=100, description="Canvas width in pixels")
    height: int = Field(default=1080, ge=100, description="Canvas height in pixels")

    def compute_positions(self) -> None:
        """Calculate x,y positions and appear_at times for each item.

        Mutates items in-place based on the layout style and animation type.
        Call this after constructing the layout and before rendering.
        """
        if not self.rows:
            return

        # Layout constants — fill the canvas, no wasted space
        title_area_height = 130  # space for title + subtitle
        category_label_width = 140  # left column for category names
        margin = 30
        gap = 14
        bottom_margin = 30

        content_left = category_label_width + margin
        content_top = title_area_height
        content_width = self.width - content_left - margin
        content_height = self.height - content_top - bottom_margin

        num_rows = len(self.rows)
        row_height = (content_height - gap * (num_rows - 1)) / max(num_rows, 1)

        # Collect all items for global indexing (used by sequential animation)
        all_items: list[InfographicItem] = []
        for row in self.rows:
            all_items.extend(row.items)
        total_items = max(len(all_items), 1)

        item_global_idx = 0

        for row_idx, row in enumerate(self.rows):
            if not row.items:
                continue

            num_items = len(row.items)
            y = content_top + row_idx * (row_height + gap)

            # Calculate item sizes and positions based on style
            if self.style == LayoutStyle.GRID:
                item_w = (content_width - gap * max(num_items - 1, 0)) / max(num_items, 1)
                item_h = row_height - 20  # leave padding above/below in the row
                for col_idx, item in enumerate(row.items):
                    x = content_left + col_idx * (item_w + gap)
                    item.position = (x, y)
                    item.size = (item_w, item_h)
                    item.appear_at = self._compute_appear_at(
                        row_idx, col_idx, num_rows, num_items,
                        item_global_idx, total_items,
                    )
                    item_global_idx += 1

            elif self.style == LayoutStyle.COMPARISON:
                # Two-column layout: split items into left and right halves
                mid = self.width / 2
                half_items = (num_items + 1) // 2
                item_w = min(120, (content_width / 2 - gap * half_items) / max(half_items, 1))
                item_h = min(item_w, row_height)
                for col_idx, item in enumerate(row.items):
                    if col_idx < half_items:
                        x = content_left + col_idx * (item_w + gap)
                    else:
                        x = mid + (col_idx - half_items) * (item_w + gap)
                    item.position = (x, y)
                    item.size = (item_w, item_h)
                    item.appear_at = self._compute_appear_at(
                        row_idx, col_idx, num_rows, num_items,
                        item_global_idx, total_items,
                    )
                    item_global_idx += 1

            elif self.style == LayoutStyle.FLOW:
                # Horizontal flow with spacing
                item_w = min(140, (content_width - gap * (num_items - 1)) / max(num_items, 1))
                item_h = min(item_w, row_height)
                for col_idx, item in enumerate(row.items):
                    x = content_left + col_idx * (item_w + gap)
                    item.position = (x, y)
                    item.size = (item_w, item_h)
                    item.appear_at = self._compute_appear_at(
                        row_idx, col_idx, num_rows, num_items,
                        item_global_idx, total_items,
                    )
                    item_global_idx += 1

            elif self.style == LayoutStyle.TIMELINE:
                # Vertical-ish timeline: items spread horizontally per row
                item_w = min(100, (content_width - gap * (num_items - 1)) / max(num_items, 1))
                item_h = min(item_w, row_height)
                for col_idx, item in enumerate(row.items):
                    x = content_left + col_idx * (item_w + gap)
                    item.position = (x, y)
                    item.size = (item_w, item_h)
                    item.appear_at = self._compute_appear_at(
                        row_idx, col_idx, num_rows, num_items,
                        item_global_idx, total_items,
                    )
                    item_global_idx += 1

    def _compute_appear_at(
        self,
        row_idx: int,
        col_idx: int,
        num_rows: int,
        num_cols: int,
        global_idx: int,
        total_items: int,
    ) -> float:
        """Compute normalized appear_at time based on animation type.

        Returns a float in [0.1, 0.85] leaving room for title fade-in at the
        start and a hold period at the end.
        """
        start = 0.1  # title shows first
        end = 0.85   # hold final frame

        if self.animation == AnimationType.SEQUENTIAL:
            # Each item one at a time, left-to-right then top-to-bottom
            if total_items <= 1:
                return start
            return start + (end - start) * global_idx / (total_items - 1)

        elif self.animation == AnimationType.ROW_BY_ROW:
            # All items in a row appear together; rows appear sequentially
            if num_rows <= 1:
                return start
            return start + (end - start) * row_idx / (num_rows - 1)

        elif self.animation == AnimationType.FADE_ALL:
            # All items appear at the same time (slight offset for visual interest)
            return start

        elif self.animation == AnimationType.BUILD_UP:
            # Bottom rows first, building upward
            if num_rows <= 1:
                return start
            inverted_row = num_rows - 1 - row_idx
            return start + (end - start) * inverted_row / (num_rows - 1)

        return start
