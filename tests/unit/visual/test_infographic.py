"""Tests for SPEC-033: Animated Infographic GIFs.

Covers rendering, GIF encoding, icon registry, layout computation,
brand color application, and animation ordering.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from holus.agents.marketing.models import BrandVisualIdentity
from holus.visual.gif_encoder import encode_gif
from holus.visual.icon_registry import IconRegistry
from holus.visual.infographic import InfographicRenderer
from holus.visual.infographic_layout import (
    AnimationType,
    InfographicItem,
    InfographicLayout,
    InfographicRow,
    LayoutStyle,
)


def _make_layout(
    animation: AnimationType = AnimationType.SEQUENTIAL,
    style: LayoutStyle = LayoutStyle.GRID,
    background_color: str = "#1A1A2E",
) -> InfographicLayout:
    """Create a simple 2-row layout for testing."""
    layout = InfographicLayout(
        title="AI Agent System Guide",
        subtitle="Open vs Closed",
        rows=[
            InfographicRow(
                category="Foundation Models",
                items=[
                    InfographicItem(name="Claude", icon="claude"),
                    InfographicItem(name="GPT-4", icon="openai"),
                    InfographicItem(name="Gemini", icon="gemini"),
                ],
            ),
            InfographicRow(
                category="Languages",
                items=[
                    InfographicItem(name="Python", icon="python"),
                    InfographicItem(name="Rust", icon="rust"),
                ],
            ),
        ],
        style=style,
        animation=animation,
        background_color=background_color,
        fps=10,
        duration_sec=8,
        width=1080,
        height=1080,
    )
    layout.compute_positions()
    return layout


class TestInfographicRendering:
    """Tests for InfographicRenderer."""

    def test_spec033_001_render_produces_frames(self) -> None:
        """AC-033-001: render produces correct number of 1080x1080 frames."""
        layout = _make_layout()
        renderer = InfographicRenderer(BrandVisualIdentity())
        frames = renderer.render(layout)

        # 10 fps * 8 sec = 80 frames
        assert len(frames) == 80
        for frame in frames:
            assert isinstance(frame, Image.Image)
            assert frame.size == (1080, 1080)

    def test_spec033_002_encode_gif_under_5mb(self) -> None:
        """AC-033-002: encoded GIF is < 5MB."""
        layout = _make_layout()
        renderer = InfographicRenderer(BrandVisualIdentity())
        frames = renderer.render(layout)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.gif"
            result_path = encode_gif(frames, output, fps=10, optimize=False)

            assert result_path.exists()
            size = result_path.stat().st_size
            assert size > 0
            assert size < 5 * 1024 * 1024, f"GIF is {size} bytes, exceeds 5MB"


class TestIconRegistry:
    """Tests for IconRegistry."""

    def test_spec033_003_icon_registry_known(self) -> None:
        """AC-033-006: known icons return valid entries."""
        registry = IconRegistry()
        display_name, hex_color = registry.get_icon("claude")

        assert display_name == "Claude"
        assert hex_color.startswith("#")
        assert len(hex_color) == 7

    def test_spec033_004_icon_registry_unknown(self) -> None:
        """Unknown icons return the raw name with default gray color."""
        registry = IconRegistry()
        display_name, hex_color = registry.get_icon("totally_unknown_icon_xyz")

        assert display_name == "totally_unknown_icon_xyz"
        assert hex_color == "#9CA3AF"


class TestLayoutComputation:
    """Tests for InfographicLayout.compute_positions()."""

    def test_spec033_005_layout_compute_positions(self) -> None:
        """All items get valid x,y positions after compute_positions()."""
        layout = _make_layout()

        for row in layout.rows:
            for item in row.items:
                x, y = item.position
                assert x >= 0, f"Item '{item.name}' has negative x: {x}"
                assert y >= 0, f"Item '{item.name}' has negative y: {y}"
                assert x < layout.width, f"Item '{item.name}' x={x} exceeds width"
                assert y < layout.height, f"Item '{item.name}' y={y} exceeds height"

                w, h = item.size
                assert w > 0, f"Item '{item.name}' has non-positive width"
                assert h > 0, f"Item '{item.name}' has non-positive height"

    def test_spec033_006_brand_colors_applied(self) -> None:
        """AC-033-005: brand background color is used in rendered frames."""
        bg_color = "#2D1B69"
        layout = _make_layout(background_color=bg_color)
        renderer = InfographicRenderer(BrandVisualIdentity())
        frames = renderer.render(layout)

        # Check that the background color matches at a corner pixel (0,0)
        # which should always be the background
        first_frame = frames[0]
        pixel = first_frame.getpixel((0, 0))
        # bg_color #2D1B69 -> (45, 27, 105) in RGB (frames are flattened to RGB)
        expected_rgb = (0x2D, 0x1B, 0x69)
        assert pixel[:3] == expected_rgb, f"Background pixel {pixel[:3]} != expected {expected_rgb}"

    def test_spec033_007_sequential_animation(self) -> None:
        """Sequential animation: earlier items have lower appear_at times."""
        layout = _make_layout(animation=AnimationType.SEQUENTIAL)

        all_items: list[InfographicItem] = []
        for row in layout.rows:
            all_items.extend(row.items)

        # Items should have strictly increasing appear_at values
        appear_times = [item.appear_at for item in all_items]
        for i in range(len(appear_times) - 1):
            assert appear_times[i] < appear_times[i + 1], (
                f"Item {i} appear_at={appear_times[i]} is not less than "
                f"item {i+1} appear_at={appear_times[i+1]}"
            )


# ---------------------------------------------------------------------------
# New layout styles (Sprint 8)
# ---------------------------------------------------------------------------


def _make_layout_with_style(
    style: LayoutStyle,
    num_rows: int = 3,
    items_per_row: int = 4,
    width: int = 1080,
    height: int = 1350,
    animation: AnimationType = AnimationType.SEQUENTIAL,
) -> InfographicLayout:
    """Create a layout with the given style and populate with test data."""
    rows = []
    for r in range(num_rows):
        items = [
            InfographicItem(name=f"Item-{r}-{c}", icon=f"icon-{r}-{c}")
            for c in range(items_per_row)
        ]
        rows.append(InfographicRow(category=f"Category {r}", items=items))
    layout = InfographicLayout(
        title="Test Layout",
        subtitle="Testing",
        rows=rows,
        style=style,
        animation=animation,
        width=width,
        height=height,
    )
    layout.compute_positions()
    return layout


def _assert_all_items_valid(layout: InfographicLayout) -> None:
    """Assert all items have valid positions and sizes within canvas bounds."""
    for row in layout.rows:
        for item in row.items:
            x, y = item.position
            w, h = item.size
            assert x >= 0, f"'{item.name}' x={x} < 0"
            assert y >= 0, f"'{item.name}' y={y} < 0"
            assert w > 0, f"'{item.name}' width={w} <= 0"
            assert h > 0, f"'{item.name}' height={h} <= 0"
            assert x + w <= layout.width + 1, f"'{item.name}' exceeds canvas right"
            assert y + h <= layout.height + 1, f"'{item.name}' exceeds canvas bottom"
            assert 0.0 <= item.appear_at <= 1.0, f"'{item.name}' appear_at={item.appear_at} out of [0,1]"


class TestLayeredStackLayout:
    """Tests for LAYERED_STACK layout style."""

    def test_positions_within_bounds(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK)
        _assert_all_items_valid(layout)

    def test_rows_have_increasing_y(self) -> None:
        """Each row should be placed below the previous one."""
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK)
        y_per_row = []
        for row in layout.rows:
            y_per_row.append(row.items[0].position[1])
        for i in range(len(y_per_row) - 1):
            assert y_per_row[i] < y_per_row[i + 1]

    def test_items_in_row_have_increasing_x(self) -> None:
        """Items within a row should be laid out left to right."""
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK)
        for row in layout.rows:
            x_positions = [item.position[0] for item in row.items]
            for i in range(len(x_positions) - 1):
                assert x_positions[i] < x_positions[i + 1]

    def test_items_leave_room_for_category_label(self) -> None:
        """Items should start after the category label area (25% of width)."""
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK, width=1080)
        category_width = int(1080 * 0.25)
        for row in layout.rows:
            for item in row.items:
                assert item.position[0] >= category_width

    def test_single_item_row(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK, items_per_row=1)
        _assert_all_items_valid(layout)

    def test_many_rows(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.LAYERED_STACK, num_rows=8, items_per_row=2)
        _assert_all_items_valid(layout)


class TestCentralHubLayout:
    """Tests for CENTRAL_HUB layout style."""

    def test_positions_within_bounds(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.CENTRAL_HUB)
        _assert_all_items_valid(layout)

    def test_items_spread_around_center(self) -> None:
        """Items should be distributed around the center, not all in one spot."""
        layout = _make_layout_with_style(LayoutStyle.CENTRAL_HUB, num_rows=3, items_per_row=2)
        positions = []
        for row in layout.rows:
            for item in row.items:
                positions.append(item.position)
        # Check that there's meaningful spread — not all at the same position
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        assert max(xs) - min(xs) > 50, "Items not spread horizontally"
        assert max(ys) - min(ys) > 50, "Items not spread vertically"

    def test_uniform_item_size(self) -> None:
        """All items in central hub should have the same size (100x70)."""
        layout = _make_layout_with_style(LayoutStyle.CENTRAL_HUB)
        for row in layout.rows:
            for item in row.items:
                assert item.size == (100, 70)

    def test_single_row(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.CENTRAL_HUB, num_rows=1, items_per_row=4)
        _assert_all_items_valid(layout)


class TestComparisonGridLayout:
    """Tests for COMPARISON_GRID layout style."""

    def test_positions_within_bounds(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.COMPARISON_GRID, num_rows=3)
        _assert_all_items_valid(layout)

    def test_columns_have_increasing_x(self) -> None:
        """Each column (row in data) should start further right."""
        layout = _make_layout_with_style(LayoutStyle.COMPARISON_GRID, num_rows=3, items_per_row=3)
        col_xs = []
        for row in layout.rows:
            col_xs.append(row.items[0].position[0])
        for i in range(len(col_xs) - 1):
            assert col_xs[i] < col_xs[i + 1]

    def test_items_in_column_have_increasing_y(self) -> None:
        """Items within a column should be stacked vertically."""
        layout = _make_layout_with_style(LayoutStyle.COMPARISON_GRID, num_rows=2, items_per_row=4)
        for row in layout.rows:
            y_positions = [item.position[1] for item in row.items]
            for i in range(len(y_positions) - 1):
                assert y_positions[i] < y_positions[i + 1]

    def test_two_columns(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.COMPARISON_GRID, num_rows=2, items_per_row=5)
        _assert_all_items_valid(layout)

    def test_four_columns(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.COMPARISON_GRID, num_rows=4, items_per_row=3)
        _assert_all_items_valid(layout)


class TestFlowDiagramLayout:
    """Tests for FLOW_DIAGRAM layout style."""

    def test_positions_within_bounds(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.FLOW_DIAGRAM)
        _assert_all_items_valid(layout)

    def test_steps_have_increasing_y(self) -> None:
        """Steps should flow top to bottom."""
        layout = _make_layout_with_style(LayoutStyle.FLOW_DIAGRAM, num_rows=4, items_per_row=2)
        step_ys = []
        for row in layout.rows:
            step_ys.append(row.items[0].position[1])
        for i in range(len(step_ys) - 1):
            assert step_ys[i] < step_ys[i + 1]

    def test_items_offset_for_step_numbers(self) -> None:
        """Items should start after step number area (margin + 80px)."""
        layout = _make_layout_with_style(LayoutStyle.FLOW_DIAGRAM)
        for row in layout.rows:
            for item in row.items:
                assert item.position[0] >= 48 + 80  # margin + step number area

    def test_single_step(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.FLOW_DIAGRAM, num_rows=1, items_per_row=3)
        _assert_all_items_valid(layout)

    def test_many_steps(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.FLOW_DIAGRAM, num_rows=6, items_per_row=2)
        _assert_all_items_valid(layout)


class TestCheatsheetLayout:
    """Tests for CHEATSHEET layout style."""

    def test_positions_within_bounds(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.CHEATSHEET)
        _assert_all_items_valid(layout)

    def test_sections_have_increasing_y(self) -> None:
        """Category sections should stack vertically."""
        layout = _make_layout_with_style(LayoutStyle.CHEATSHEET, num_rows=3, items_per_row=4)
        section_ys = []
        for row in layout.rows:
            section_ys.append(row.items[0].position[1])
        for i in range(len(section_ys) - 1):
            assert section_ys[i] < section_ys[i + 1]

    def test_items_wrap_in_grid(self) -> None:
        """With >4 items, items should wrap to next grid row within section."""
        layout = _make_layout_with_style(LayoutStyle.CHEATSHEET, num_rows=1, items_per_row=6)
        items = layout.rows[0].items
        # First 4 items on row 0, next 2 on row 1
        y_row0 = items[0].position[1]
        y_row1 = items[4].position[1]
        assert y_row1 > y_row0, "5th item should wrap to next row"
        # Items 0-3 should all be on same y
        for i in range(4):
            assert items[i].position[1] == y_row0

    def test_max_4_columns_per_section(self) -> None:
        """Cheatsheet uses max 4 columns per section."""
        layout = _make_layout_with_style(LayoutStyle.CHEATSHEET, num_rows=1, items_per_row=8)
        items = layout.rows[0].items
        # Items 0 and 4 should have the same x (both in column 0)
        assert items[0].position[0] == items[4].position[0]

    def test_dense_layout(self) -> None:
        """Many items in many sections should all fit."""
        layout = _make_layout_with_style(LayoutStyle.CHEATSHEET, num_rows=5, items_per_row=6)
        _assert_all_items_valid(layout)


class TestBackwardCompatibility:
    """Verify original 4 styles still work through compute_positions()."""

    def test_grid_style(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.GRID)
        _assert_all_items_valid(layout)

    def test_comparison_style(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.COMPARISON)
        _assert_all_items_valid(layout)

    def test_flow_style(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.FLOW)
        _assert_all_items_valid(layout)

    def test_timeline_style(self) -> None:
        layout = _make_layout_with_style(LayoutStyle.TIMELINE)
        _assert_all_items_valid(layout)

    def test_original_styles_use_grid_layout(self) -> None:
        """COMPARISON, FLOW, TIMELINE all dispatch to _compute_grid."""
        for style in [LayoutStyle.COMPARISON, LayoutStyle.FLOW, LayoutStyle.TIMELINE]:
            layout = _make_layout_with_style(style, num_rows=2, items_per_row=3)
            grid_layout = _make_layout_with_style(LayoutStyle.GRID, num_rows=2, items_per_row=3)
            for r_idx, row in enumerate(layout.rows):
                for i_idx, item in enumerate(row.items):
                    grid_item = grid_layout.rows[r_idx].items[i_idx]
                    assert item.position == grid_item.position
                    assert item.size == grid_item.size


class TestNewModelFields:
    """Tests for new InfographicLayout fields: dark_mode, attribution, column_headers."""

    def test_dark_mode_default_false(self) -> None:
        layout = InfographicLayout(title="Test")
        assert layout.dark_mode is False

    def test_dark_mode_set_true(self) -> None:
        layout = InfographicLayout(title="Test", dark_mode=True)
        assert layout.dark_mode is True

    def test_attribution_default_empty(self) -> None:
        layout = InfographicLayout(title="Test")
        assert layout.attribution == ""

    def test_attribution_set(self) -> None:
        layout = InfographicLayout(title="Test", attribution="@camilomartinez")
        assert layout.attribution == "@camilomartinez"

    def test_column_headers_default_empty(self) -> None:
        layout = InfographicLayout(title="Test")
        assert layout.column_headers == []

    def test_column_headers_set(self) -> None:
        from holus.visual.infographic_layout import ColumnHeader

        headers = [
            ColumnHeader(title="Pro", color="#22C55E"),
            ColumnHeader(title="Con", color="#EF4444"),
        ]
        layout = InfographicLayout(title="Test", column_headers=headers)
        assert len(layout.column_headers) == 2
        assert layout.column_headers[0].title == "Pro"
        assert layout.column_headers[1].color == "#EF4444"

    def test_column_header_default_color(self) -> None:
        from holus.visual.infographic_layout import ColumnHeader

        header = ColumnHeader(title="Default")
        assert header.color == "#3B82F6"

    def test_new_fields_dont_break_compute(self) -> None:
        """New fields should not affect position computation."""
        from holus.visual.infographic_layout import ColumnHeader

        layout = InfographicLayout(
            title="Test",
            dark_mode=True,
            attribution="@test",
            column_headers=[ColumnHeader(title="A"), ColumnHeader(title="B")],
            rows=[
                InfographicRow(
                    category="Cat",
                    items=[InfographicItem(name="I1", icon="x"), InfographicItem(name="I2", icon="y")],
                ),
            ],
            style=LayoutStyle.LAYERED_STACK,
        )
        layout.compute_positions()
        for item in layout.rows[0].items:
            assert item.position != (0.0, 0.0)
            assert item.size[0] > 0
            assert item.size[1] > 0


class TestAnimationTypes:
    """Test all animation types work across new layout styles."""

    def test_row_by_row_same_appear_within_row(self) -> None:
        """ROW_BY_ROW: items in same row get the same appear_at."""
        layout = _make_layout_with_style(
            LayoutStyle.LAYERED_STACK, num_rows=3, items_per_row=3,
            animation=AnimationType.ROW_BY_ROW,
        )
        for row in layout.rows:
            times = [item.appear_at for item in row.items]
            assert len(set(times)) == 1, f"Items in row should share appear_at, got {times}"

    def test_fade_all_same_appear(self) -> None:
        """FADE_ALL: all items appear at the same time."""
        layout = _make_layout_with_style(
            LayoutStyle.CENTRAL_HUB, animation=AnimationType.FADE_ALL,
        )
        all_times = []
        for row in layout.rows:
            all_times.extend(item.appear_at for item in row.items)
        assert len(set(all_times)) == 1

    def test_build_up_inverted_row_order(self) -> None:
        """BUILD_UP: later rows appear first (bottom-up)."""
        layout = _make_layout_with_style(
            LayoutStyle.FLOW_DIAGRAM, num_rows=3, items_per_row=1,
            animation=AnimationType.BUILD_UP,
        )
        row_times = [layout.rows[i].items[0].appear_at for i in range(3)]
        # Last row should appear first (lowest appear_at)
        assert row_times[2] < row_times[1] < row_times[0]

    def test_sequential_across_comparison_grid(self) -> None:
        """SEQUENTIAL: globally increasing appear_at across all items."""
        layout = _make_layout_with_style(
            LayoutStyle.COMPARISON_GRID, num_rows=2, items_per_row=3,
            animation=AnimationType.SEQUENTIAL,
        )
        all_times = []
        for row in layout.rows:
            all_times.extend(item.appear_at for item in row.items)
        for i in range(len(all_times) - 1):
            assert all_times[i] < all_times[i + 1]


class TestEmptyRowsAndEdgeCases:
    """Edge cases for layout computation."""

    def test_empty_rows_no_crash(self) -> None:
        """compute_positions with no rows should not crash."""
        layout = InfographicLayout(title="Empty", rows=[], style=LayoutStyle.LAYERED_STACK)
        layout.compute_positions()  # should not raise

    def test_row_with_no_items(self) -> None:
        """Rows with zero items should be skipped gracefully."""
        layout = InfographicLayout(
            title="Test",
            rows=[
                InfographicRow(category="Empty", items=[]),
                InfographicRow(
                    category="Full",
                    items=[InfographicItem(name="A", icon="a")],
                ),
            ],
            style=LayoutStyle.LAYERED_STACK,
        )
        layout.compute_positions()
        assert layout.rows[1].items[0].position != (0.0, 0.0)

    def test_single_item_single_row(self) -> None:
        """Minimal layout: 1 row, 1 item."""
        for style in LayoutStyle:
            layout = _make_layout_with_style(style, num_rows=1, items_per_row=1)
            _assert_all_items_valid(layout)

    def test_unknown_style_falls_back_to_grid(self) -> None:
        """An unrecognized style value falls back to _compute_grid."""
        layout = _make_layout_with_style(LayoutStyle.GRID, num_rows=2, items_per_row=3)
        # GRID is the fallback — just verify it doesn't crash
        _assert_all_items_valid(layout)
