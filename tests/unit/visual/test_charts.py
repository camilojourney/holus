"""Tests for SVG chart generators."""

from holus.visual.charts import (
    bar_chart_svg,
    decorative_svg,
    donut_svg,
    flowchart_svg,
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


class TestFlowchart:
    def test_empty_returns_empty(self):
        assert flowchart_svg([], []) == ""

    def test_vertical_layout_renders_escaped_nodes_and_edge_labels(self):
        svg = flowchart_svg(
            [
                {"id": "start", "label": "Read & plan", "description": "Input <thought>"},
                {"id": "done", "label": "Publish", "description": ""},
            ],
            [{"from_id": "start", "to_id": "done", "label": "then & now"}],
        )

        assert 'aria-label="Flowchart"' in svg
        assert "Read &amp; plan" in svg
        assert "Input &lt;thought&gt;" in svg
        assert "then &amp; now" in svg
        assert 'stroke-width="4"' in svg

    def test_horizontal_layout_uses_horizontal_edges(self):
        svg = flowchart_svg(
            [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            [{"from_id": "a", "to_id": "b", "label": "next"}],
            layout="horizontal",
        )

        assert 'stroke-width="2"' in svg
        assert 'text-anchor="middle"' in svg
        assert "next" in svg

    def test_grid_layout_omits_connectors(self):
        svg = flowchart_svg(
            [{"id": str(index), "label": f"Node {index}"} for index in range(4)],
            [{"from_id": "0", "to_id": "1", "label": "hidden"}],
            layout="grid",
        )

        assert 'viewBox="0 0 940 340"' in svg
        assert "hidden" not in svg
        assert 'marker id="fc-arrow"' in svg

    def test_invalid_edge_is_ignored(self):
        svg = flowchart_svg(
            [{"id": "only", "label": "Only"}],
            [{"from_id": "missing", "to_id": "only", "label": "ignored"}],
        )

        assert "ignored" not in svg


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
