"""Tests for SVG chart generators."""

from holus.visual.charts import (
    bar_chart_svg,
    decorative_svg,
    donut_svg,
    list_patterns,
    sparkline_svg,
)


class TestSparkline:
    def test_basic(self):
        svg = sparkline_svg([10, 30, 25, 45, 40, 60])
        assert svg.startswith("<svg")
        assert "polyline" in svg
        assert "polygon" in svg

    def test_empty_returns_empty(self):
        assert sparkline_svg([]) == ""
        assert sparkline_svg([42]) == ""

    def test_flat_values(self):
        svg = sparkline_svg([5, 5, 5, 5])
        assert "polyline" in svg

    def test_custom_dimensions(self):
        svg = sparkline_svg([1, 2, 3], width=200, height=40)
        assert 'width="200"' in svg
        assert 'height="40"' in svg


class TestBarChart:
    def test_basic(self):
        svg = bar_chart_svg({"A": 100, "B": 50, "C": 75})
        assert svg.startswith("<svg")
        assert "rect" in svg
        assert ">A<" in svg
        assert ">B<" in svg

    def test_empty_returns_empty(self):
        assert bar_chart_svg({}) == ""

    def test_single_bar(self):
        svg = bar_chart_svg({"Only": 42})
        assert "Only" in svg
        assert "42" in svg


class TestDonut:
    def test_basic(self):
        svg = donut_svg(73)
        assert svg.startswith("<svg")
        assert "circle" in svg
        assert "stroke-dasharray" in svg

    def test_with_label(self):
        svg = donut_svg(50, label="50%")
        assert "50%" in svg

    def test_zero_percent(self):
        svg = donut_svg(0)
        assert "0.0" in svg

    def test_full_percent(self):
        svg = donut_svg(100)
        assert svg.startswith("<svg")


class TestDecorative:
    def test_circles(self):
        svg = decorative_svg("circles")
        assert "<circle" in svg

    def test_grid(self):
        svg = decorative_svg("grid")
        assert "<circle" in svg

    def test_waves(self):
        svg = decorative_svg("waves")
        assert "<path" in svg

    def test_blocks(self):
        svg = decorative_svg("blocks")
        assert "<rect" in svg

    def test_unknown_fallback(self):
        svg = decorative_svg("nonexistent")
        assert "<circle" in svg  # falls back to circles

    def test_list_patterns(self):
        patterns = list_patterns()
        assert "circles" in patterns
        assert "grid" in patterns
        assert "waves" in patterns
        assert "blocks" in patterns
        assert len(patterns) >= 4
