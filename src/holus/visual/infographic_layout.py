"""Pydantic models for infographic layout and animation timing.

Describes the structured data that drives infographic rendering:
rows of categorized items, layout style, animation type, and dimensions.

Supports 5 layout templates from the style guide:
- LAYERED_STACK: horizontal rows with category + icons (default, LinkedIn-optimal)
- CENTRAL_HUB: center element + surrounding cards
- COMPARISON_GRID: 2-4 columns side by side
- FLOW_DIAGRAM: numbered steps with arrows
- CHEATSHEET: dense grid of labeled items in categories
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LayoutStyle(StrEnum):
    """Layout arrangement for infographic items."""

    # Original styles (kept for backward compatibility)
    GRID = "grid"
    COMPARISON = "comparison"
    FLOW = "flow"
    TIMELINE = "timeline"

    # New style-guide templates
    LAYERED_STACK = "layered-stack"
    CENTRAL_HUB = "central-hub"
    COMPARISON_GRID = "comparison-grid"
    FLOW_DIAGRAM = "flow-diagram"
    CHEATSHEET = "cheatsheet"


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
    description: str = Field(
        default="", description="Optional description for the category"
    )


class ColumnHeader(BaseModel):
    """Header for a comparison column."""

    title: str = Field(description="Column header text")
    color: str = Field(default="#3B82F6", description="Header accent color")


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
        default="#FFFFFF", description="Background hex color"
    )
    dark_mode: bool = Field(
        default=False, description="Use dark color scheme"
    )
    fps: int = Field(default=18, ge=1, le=30, description="Frames per second")
    duration_sec: int = Field(
        default=10, ge=1, le=40, description="Animation duration in seconds"
    )
    width: int = Field(default=1080, ge=100, description="Canvas width in pixels")
    height: int = Field(default=1350, ge=100, description="Canvas height in pixels")
    attribution: str = Field(
        default="", description="Creator attribution text (top-right)"
    )
    column_headers: list[ColumnHeader] = Field(
        default_factory=list, description="Column headers for comparison layouts"
    )

    def compute_positions(self) -> None:
        """Calculate x,y positions and appear_at times for each item.

        Mutates items in-place based on the layout style and animation type.
        Call this after constructing the layout and before rendering.
        """
        if not self.rows:
            return

        style_dispatch = {
            LayoutStyle.LAYERED_STACK: self._compute_layered_stack,
            LayoutStyle.CENTRAL_HUB: self._compute_central_hub,
            LayoutStyle.COMPARISON_GRID: self._compute_comparison_grid,
            LayoutStyle.FLOW_DIAGRAM: self._compute_flow_diagram,
            LayoutStyle.CHEATSHEET: self._compute_cheatsheet,
            LayoutStyle.GRID: self._compute_grid,
            LayoutStyle.COMPARISON: self._compute_grid,
            LayoutStyle.FLOW: self._compute_grid,
            LayoutStyle.TIMELINE: self._compute_grid,
        }
        compute_fn = style_dispatch.get(self.style, self._compute_grid)
        compute_fn()

    def _compute_layered_stack(self) -> None:
        """Layered stack: full-width rows, category on left, icons on right.

        Matches the ByteByteGo / Brij Pandey horizontal layered stack style.
        """
        margin = 48
        title_area_height = 160
        row_gap = 24
        bottom_margin = 48

        category_width = int(self.width * 0.25)
        content_left = margin + category_width + 16
        content_right = self.width - margin

        num_rows = len(self.rows)
        available_height = self.height - title_area_height - bottom_margin
        row_height = (available_height - row_gap * max(num_rows - 1, 0)) / max(num_rows, 1)
        row_height = min(row_height, 120)

        item_global_idx = 0
        total_items = sum(len(r.items) for r in self.rows)

        for row_idx, row in enumerate(self.rows):
            if not row.items:
                continue

            y = title_area_height + row_idx * (row_height + row_gap)
            num_items = len(row.items)
            item_gap = 16
            available_w = content_right - content_left
            item_w = min(100, (available_w - item_gap * max(num_items - 1, 0)) / max(num_items, 1))
            item_h = min(row_height - 16, item_w)

            # Center items vertically in the row
            item_y = y + (row_height - item_h) / 2

            for col_idx, item in enumerate(row.items):
                x = content_left + col_idx * (item_w + item_gap)
                item.position = (x, item_y)
                item.size = (item_w, item_h)
                item.appear_at = self._compute_appear_at(
                    row_idx, col_idx, num_rows, num_items,
                    item_global_idx, total_items,
                )
                item_global_idx += 1

    def _compute_central_hub(self) -> None:
        """Central hub: center element with surrounding section cards."""
        import math

        margin = 48
        title_area_height = 140
        center_x = self.width / 2
        center_y = (self.height + title_area_height) / 2
        radius = min(self.width, self.height - title_area_height) * 0.32

        total_items = sum(len(r.items) for r in self.rows)
        item_global_idx = 0
        num_rows = len(self.rows)

        for row_idx, row in enumerate(self.rows):
            if not row.items:
                continue

            num_items = len(row.items)
            angle_start = (2 * math.pi * row_idx) / max(num_rows, 1)
            angle_step = (2 * math.pi / max(num_rows, 1)) / max(num_items + 1, 2)

            for col_idx, item in enumerate(row.items):
                angle = angle_start + (col_idx + 1) * angle_step
                x = center_x + radius * math.cos(angle) - 50
                y = center_y + radius * math.sin(angle) - 35
                x = max(margin, min(x, self.width - margin - 100))
                y = max(title_area_height, min(y, self.height - margin - 70))
                item.position = (x, y)
                item.size = (100, 70)
                item.appear_at = self._compute_appear_at(
                    row_idx, col_idx, num_rows, num_items,
                    item_global_idx, total_items,
                )
                item_global_idx += 1

    def _compute_comparison_grid(self) -> None:
        """Comparison grid: 2-4 equal-width columns side by side."""
        margin = 48
        title_area_height = 160
        col_gap = 16
        row_gap = 12
        bottom_margin = 48

        num_cols = len(self.rows)
        col_width = (self.width - 2 * margin - col_gap * max(num_cols - 1, 0)) / max(num_cols, 1)

        total_items = sum(len(r.items) for r in self.rows)
        item_global_idx = 0

        max_items = max((len(r.items) for r in self.rows), default=1)
        available_height = self.height - title_area_height - bottom_margin - 48  # header space
        item_h = min(60, (available_height - row_gap * max(max_items - 1, 0)) / max(max_items, 1))

        for col_idx, row in enumerate(self.rows):
            if not row.items:
                continue

            col_x = margin + col_idx * (col_width + col_gap)
            num_items = len(row.items)

            for item_idx, item in enumerate(row.items):
                y = title_area_height + 48 + item_idx * (item_h + row_gap)
                item.position = (col_x + 8, y)
                item.size = (col_width - 16, item_h)
                item.appear_at = self._compute_appear_at(
                    col_idx, item_idx, num_cols, num_items,
                    item_global_idx, total_items,
                )
                item_global_idx += 1

    def _compute_flow_diagram(self) -> None:
        """Flow diagram: numbered steps top-to-bottom."""
        margin = 48
        title_area_height = 160
        step_gap = 24
        bottom_margin = 48

        total_items = sum(len(r.items) for r in self.rows)
        item_global_idx = 0
        num_rows = len(self.rows)

        available_height = self.height - title_area_height - bottom_margin
        step_height = (available_height - step_gap * max(num_rows - 1, 0)) / max(num_rows, 1)
        step_height = min(step_height, 100)
        step_width = self.width - 2 * margin - 80  # leave room for step numbers

        for row_idx, row in enumerate(self.rows):
            y = title_area_height + row_idx * (step_height + step_gap)
            num_items = len(row.items)
            item_gap = 12
            item_w = min(120, (step_width - item_gap * max(num_items - 1, 0)) / max(num_items, 1))

            for col_idx, item in enumerate(row.items):
                x = margin + 80 + col_idx * (item_w + item_gap)
                item.position = (x, y + 8)
                item.size = (item_w, step_height - 16)
                item.appear_at = self._compute_appear_at(
                    row_idx, col_idx, num_rows, num_items,
                    item_global_idx, total_items,
                )
                item_global_idx += 1

    def _compute_cheatsheet(self) -> None:
        """Cheatsheet: dense grid organized into category sections."""
        margin = 48
        title_area_height = 140
        section_gap = 20
        item_gap = 12
        bottom_margin = 48

        num_rows = len(self.rows)
        available_height = self.height - title_area_height - bottom_margin
        section_height = (available_height - section_gap * max(num_rows - 1, 0)) / max(num_rows, 1)

        total_items = sum(len(r.items) for r in self.rows)
        item_global_idx = 0
        content_width = self.width - 2 * margin

        for row_idx, row in enumerate(self.rows):
            if not row.items:
                continue

            section_y = title_area_height + row_idx * (section_height + section_gap)
            num_items = len(row.items)

            # Arrange in a grid within the section
            cols_per_section = min(4, num_items)
            item_w = (content_width - item_gap * max(cols_per_section - 1, 0)) / max(cols_per_section, 1)
            item_h = min(50, section_height - 32)

            for col_idx, item in enumerate(row.items):
                grid_col = col_idx % cols_per_section
                grid_row = col_idx // cols_per_section
                x = margin + grid_col * (item_w + item_gap)
                y = section_y + 28 + grid_row * (item_h + item_gap)
                item.position = (x, y)
                item.size = (item_w, item_h)
                item.appear_at = self._compute_appear_at(
                    row_idx, col_idx, num_rows, num_items,
                    item_global_idx, total_items,
                )
                item_global_idx += 1

    def _compute_grid(self) -> None:
        """Original grid layout (backward compatible)."""
        title_area_height = 130
        category_label_width = 140
        margin = 30
        gap = 14
        bottom_margin = 30

        content_left = category_label_width + margin
        content_top = title_area_height
        content_width = self.width - content_left - margin
        content_height = self.height - content_top - bottom_margin

        num_rows = len(self.rows)
        row_height = (content_height - gap * (num_rows - 1)) / max(num_rows, 1)

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

            item_w = (content_width - gap * max(num_items - 1, 0)) / max(num_items, 1)
            item_h = row_height - 20

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
            if total_items <= 1:
                return start
            return start + (end - start) * global_idx / (total_items - 1)

        elif self.animation == AnimationType.ROW_BY_ROW:
            if num_rows <= 1:
                return start
            return start + (end - start) * row_idx / (num_rows - 1)

        elif self.animation == AnimationType.FADE_ALL:
            return start

        elif self.animation == AnimationType.BUILD_UP:
            if num_rows <= 1:
                return start
            inverted_row = num_rows - 1 - row_idx
            return start + (end - start) * inverted_row / (num_rows - 1)

        return start
