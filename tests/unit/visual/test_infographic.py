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
