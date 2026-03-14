"""Tests for visual spec converter functions.

Covers all 3 converter functions (data_viz_to_spec, before_after_to_spec,
insight_to_spec) plus edge cases and validation.
"""

from __future__ import annotations

import pytest

from holus.visual.models import OutputFormat, RenderSpec
from holus.visual.spec_converter import (
    before_after_to_spec,
    data_viz_to_spec,
    insight_to_spec,
)

# ---------------------------------------------------------------------------
# data_viz_to_spec
# ---------------------------------------------------------------------------


class TestDataVizToSpec:
    """Test data_viz_to_spec converter."""

    def _minimal_input(self) -> dict:
        return {
            "chart_type": "bar",
            "title": "Weekly Downloads",
            "data_points": [
                {"label": "Mon", "value": 100},
                {"label": "Tue", "value": 250},
            ],
        }

    def test_minimal_valid_input(self):
        spec = data_viz_to_spec(self._minimal_input())
        assert isinstance(spec, RenderSpec)
        assert spec.template == "single_image/data_viz"
        assert spec.variables["chart_type"] == "bar"
        assert spec.variables["title"] == "Weekly Downloads"
        assert spec.variables["labels"] == ["Mon", "Tue"]
        assert spec.variables["values"] == ["100", "250"]
        assert spec.output_format == OutputFormat.PNG

    def test_default_viewport(self):
        spec = data_viz_to_spec(self._minimal_input())
        assert spec.viewport_width == 1080
        assert spec.viewport_height == 1080

    def test_custom_viewport(self):
        spec = data_viz_to_spec(
            self._minimal_input(),
            viewport_width=1200,
            viewport_height=628,
        )
        assert spec.viewport_width == 1200
        assert spec.viewport_height == 628

    def test_pdf_output_format(self):
        spec = data_viz_to_spec(
            self._minimal_input(),
            output_format=OutputFormat.PDF,
        )
        assert spec.output_format == OutputFormat.PDF

    def test_with_highlight_index(self):
        data = {**self._minimal_input(), "highlight_index": 1}
        spec = data_viz_to_spec(data)
        assert spec.variables["highlight_index"] == 1

    def test_without_highlight_index(self):
        spec = data_viz_to_spec(self._minimal_input())
        assert "highlight_index" not in spec.variables

    def test_with_source_label(self):
        data = {**self._minimal_input(), "source_label": "Source: Analytics API"}
        spec = data_viz_to_spec(data)
        assert spec.variables["source_label"] == "Source: Analytics API"

    def test_default_source_label_empty(self):
        spec = data_viz_to_spec(self._minimal_input())
        assert spec.variables["source_label"] == ""

    def test_with_color_scheme(self):
        data = {**self._minimal_input(), "color_scheme": "warm"}
        spec = data_viz_to_spec(data)
        assert spec.variables["color_scheme"] == "warm"

    def test_without_color_scheme(self):
        spec = data_viz_to_spec(self._minimal_input())
        assert "color_scheme" not in spec.variables

    def test_missing_chart_type_raises(self):
        data = self._minimal_input()
        del data["chart_type"]
        with pytest.raises(ValueError, match="chart_type"):
            data_viz_to_spec(data)

    def test_missing_title_raises(self):
        data = self._minimal_input()
        del data["title"]
        with pytest.raises(ValueError, match="title"):
            data_viz_to_spec(data)

    def test_missing_data_points_raises(self):
        data = self._minimal_input()
        del data["data_points"]
        with pytest.raises(ValueError, match="data_points"):
            data_viz_to_spec(data)

    def test_empty_data_points_raises(self):
        data = {**self._minimal_input(), "data_points": []}
        with pytest.raises(ValueError, match="non-empty"):
            data_viz_to_spec(data)

    def test_data_points_not_list_raises(self):
        data = {**self._minimal_input(), "data_points": "not a list"}
        with pytest.raises(ValueError, match="non-empty"):
            data_viz_to_spec(data)

    def test_data_point_missing_label_defaults_empty(self):
        data = {**self._minimal_input(), "data_points": [{"value": 42}]}
        spec = data_viz_to_spec(data)
        assert spec.variables["labels"] == [""]

    def test_data_point_missing_value_defaults_zero(self):
        data = {**self._minimal_input(), "data_points": [{"label": "X"}]}
        spec = data_viz_to_spec(data)
        assert spec.variables["values"] == ["0"]

    def test_many_data_points(self):
        points = [{"label": f"Day {i}", "value": i * 10} for i in range(20)]
        data = {**self._minimal_input(), "data_points": points}
        spec = data_viz_to_spec(data)
        assert len(spec.variables["labels"]) == 20


# ---------------------------------------------------------------------------
# before_after_to_spec
# ---------------------------------------------------------------------------


class TestBeforeAfterToSpec:
    """Test before_after_to_spec converter."""

    def _minimal_input(self) -> dict:
        return {
            "headline": "Workflow Improvements",
            "before_description": "Manual 5-step process",
            "after_description": "One-click automation",
        }

    def test_minimal_valid_input(self):
        spec = before_after_to_spec(self._minimal_input())
        assert isinstance(spec, RenderSpec)
        assert spec.template == "single_image/before_after"
        assert spec.variables["headline"] == "Workflow Improvements"
        assert spec.variables["before_description"] == "Manual 5-step process"
        assert spec.variables["after_description"] == "One-click automation"

    def test_default_labels(self):
        spec = before_after_to_spec(self._minimal_input())
        assert spec.variables["before_label"] == "Before"
        assert spec.variables["after_label"] == "After"

    def test_custom_labels(self):
        data = {**self._minimal_input(), "before_label": "Old", "after_label": "New"}
        spec = before_after_to_spec(data)
        assert spec.variables["before_label"] == "Old"
        assert spec.variables["after_label"] == "New"

    def test_with_product(self):
        data = {**self._minimal_input(), "product": "pilaster"}
        spec = before_after_to_spec(data)
        assert spec.variables["product"] == "pilaster"

    def test_default_product_empty(self):
        spec = before_after_to_spec(self._minimal_input())
        assert spec.variables["product"] == ""

    def test_with_image_urls(self):
        data = {
            **self._minimal_input(),
            "before_image_url": "https://example.com/before.png",
            "after_image_url": "https://example.com/after.png",
        }
        spec = before_after_to_spec(data)
        assert spec.variables["before_image_url"] == "https://example.com/before.png"
        assert spec.variables["after_image_url"] == "https://example.com/after.png"

    def test_without_image_urls(self):
        spec = before_after_to_spec(self._minimal_input())
        assert "before_image_url" not in spec.variables
        assert "after_image_url" not in spec.variables

    def test_missing_headline_raises(self):
        data = self._minimal_input()
        del data["headline"]
        with pytest.raises(ValueError, match="headline"):
            before_after_to_spec(data)

    def test_missing_before_description_raises(self):
        data = self._minimal_input()
        del data["before_description"]
        with pytest.raises(ValueError, match="before_description"):
            before_after_to_spec(data)

    def test_missing_after_description_raises(self):
        data = self._minimal_input()
        del data["after_description"]
        with pytest.raises(ValueError, match="after_description"):
            before_after_to_spec(data)

    def test_pdf_format(self):
        spec = before_after_to_spec(
            self._minimal_input(),
            output_format=OutputFormat.PDF,
        )
        assert spec.output_format == OutputFormat.PDF

    def test_custom_viewport(self):
        spec = before_after_to_spec(
            self._minimal_input(),
            viewport_width=1920,
            viewport_height=1080,
        )
        assert spec.viewport_width == 1920
        assert spec.viewport_height == 1080


# ---------------------------------------------------------------------------
# insight_to_spec
# ---------------------------------------------------------------------------


class TestInsightToSpec:
    """Test insight_to_spec converter."""

    def test_text_only(self):
        spec = insight_to_spec("AI adoption grew 3x in 2025")
        assert isinstance(spec, RenderSpec)
        assert spec.template == "single_image/insight"
        assert spec.variables["text"] == "AI adoption grew 3x in 2025"

    def test_text_with_stat(self):
        spec = insight_to_spec("Performance improved significantly", stat="4.2x faster")
        assert spec.variables["stat"] == "4.2x faster"

    def test_text_with_quote(self):
        spec = insight_to_spec(
            "Expert opinion on AI trends",
            quote="The future is autonomous agents.",
        )
        assert spec.variables["quote"] == "The future is autonomous agents."

    def test_text_with_stat_and_quote(self):
        spec = insight_to_spec(
            "Key finding",
            stat="92%",
            quote="Nearly all respondents agreed.",
        )
        assert spec.variables["text"] == "Key finding"
        assert spec.variables["stat"] == "92%"
        assert spec.variables["quote"] == "Nearly all respondents agreed."

    def test_stat_none_excluded(self):
        spec = insight_to_spec("Just text")
        assert "stat" not in spec.variables

    def test_quote_none_excluded(self):
        spec = insight_to_spec("Just text")
        assert "quote" not in spec.variables

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            insight_to_spec("")

    def test_whitespace_only_text_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            insight_to_spec("   ")

    def test_text_stripped(self):
        spec = insight_to_spec("  leading and trailing spaces  ")
        assert spec.variables["text"] == "leading and trailing spaces"

    def test_stat_stripped(self):
        spec = insight_to_spec("text", stat="  42%  ")
        assert spec.variables["stat"] == "42%"

    def test_quote_stripped(self):
        spec = insight_to_spec("text", quote="  wise words  ")
        assert spec.variables["quote"] == "wise words"

    def test_default_viewport(self):
        spec = insight_to_spec("test")
        assert spec.viewport_width == 1080
        assert spec.viewport_height == 1080

    def test_custom_viewport(self):
        spec = insight_to_spec("test", viewport_width=800, viewport_height=600)
        assert spec.viewport_width == 800
        assert spec.viewport_height == 600

    def test_pdf_format(self):
        spec = insight_to_spec("test", output_format=OutputFormat.PDF)
        assert spec.output_format == OutputFormat.PDF

    def test_long_text(self):
        long_text = "A" * 5000
        spec = insight_to_spec(long_text)
        assert spec.variables["text"] == long_text


# ---------------------------------------------------------------------------
# Cross-cutting / integration
# ---------------------------------------------------------------------------


class TestSpecConverterIntegration:
    """Cross-cutting tests for all converters."""

    def test_all_return_render_spec(self):
        """Every converter returns RenderSpec."""
        specs = [
            data_viz_to_spec({
                "chart_type": "line",
                "title": "Test",
                "data_points": [{"label": "a", "value": 1}],
            }),
            before_after_to_spec({
                "headline": "Test",
                "before_description": "old",
                "after_description": "new",
            }),
            insight_to_spec("test insight"),
        ]
        for spec in specs:
            assert isinstance(spec, RenderSpec)

    def test_all_use_single_image_templates(self):
        """All converters target single_image/ templates."""
        specs = [
            data_viz_to_spec({
                "chart_type": "bar",
                "title": "T",
                "data_points": [{"label": "x", "value": 1}],
            }),
            before_after_to_spec({
                "headline": "H",
                "before_description": "b",
                "after_description": "a",
            }),
            insight_to_spec("text"),
        ]
        for spec in specs:
            assert spec.template.startswith("single_image/")

    def test_default_timeout(self):
        """All specs get the default 30s timeout."""
        spec = insight_to_spec("test")
        assert spec.timeout_ms == 30_000
