from __future__ import annotations

import pytest

from holus.visual.chart import generate_svg
from holus.visual.spec_converter import data_viz_to_spec


def test_bar_chart_returns_svg() -> None:
    svg = generate_svg("bar", ["A", "B", "C"], ["10", "20", "30"])

    assert svg.startswith("<svg")
    assert "rect" in svg


def test_line_chart_returns_svg() -> None:
    svg = generate_svg("line", ["Jan", "Feb"], ["5", "8"])

    assert "polyline" in svg or "path" in svg


def test_metric_chart_returns_svg() -> None:
    svg = generate_svg("metric", ["Users"], ["42k"])

    assert "42k" in svg


def test_highlight_index() -> None:
    svg = generate_svg("bar", ["A", "B"], ["5", "10"], highlight_index=1)

    assert "#6366f1" in svg


def test_invalid_type_raises() -> None:
    with pytest.raises(ValueError):
        generate_svg("pie", ["A"], ["1"])


def test_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError):
        generate_svg("bar", ["A", "B"], ["1"])


def test_data_viz_to_spec_svg_content() -> None:
    spec = data_viz_to_spec({
        "chart_type": "bar",
        "title": "Growth",
        "data_points": [{"label": "Q1", "value": 10}],
    })

    assert "svg_content" in spec.variables
    assert spec.template == "single_image/data_viz"
