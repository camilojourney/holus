"""Tests for carousel PDF rendering pipeline.

Covers:
- carousel_spec_to_slides conversion from agent JSON
- Template rendering for summary_slide (new template)
- render_carousel_pdf with correct page dimensions
- render_carousel_visual convenience function
- Edge cases (empty slides, missing fields, unknown types)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.visual.carousel_builder import _normalize_outline
from holus.visual.engine import PlaywrightEngine
from holus.visual.models import CarouselSpec, OutputFormat, SlideSpec
from holus.visual.spec_converter import carousel_spec_to_slides
from holus.visual.templates import TemplateEngine

# ---------------------------------------------------------------------------
# carousel_spec_to_slides
# ---------------------------------------------------------------------------


class TestNormalizeOutlineDesign:
    """Test _normalize_outline design block merging."""

    def test_design_merged_into_slide_variables(self):
        outline = {
            "slides": [
                {"type": "hook", "variables": {"headline": "Test"}},
                {"type": "body", "variables": {"title": "B"}},
            ],
            "design": {
                "theme": "warm",
                "font_pairing": "editorial",
                "gradient": "warm_sunset",
                "effect": "glass",
            },
        }
        result = _normalize_outline(outline)
        for slide in result["slides"]:
            assert slide["variables"]["theme"] == "warm"
            assert slide["variables"]["font_pairing"] == "editorial"
            assert slide["variables"]["background_gradient"] == "warm_sunset"
            assert slide["variables"]["visual_effect"] == "glass"

    def test_design_none_effect_not_merged(self):
        outline = {
            "slides": [{"type": "hook", "variables": {}}],
            "design": {"effect": "none"},
        }
        result = _normalize_outline(outline)
        assert "visual_effect" not in result["slides"][0]["variables"]

    def test_no_design_block_works(self):
        outline = {
            "slides": [{"type": "hook", "variables": {"headline": "X"}}],
        }
        result = _normalize_outline(outline)
        assert "theme" not in result["slides"][0]["variables"]

    def test_slide_level_overrides_design(self):
        outline = {
            "slides": [{"type": "hook", "variables": {"headline": "X", "theme": "bold"}}],
            "design": {"theme": "dark"},
        }
        result = _normalize_outline(outline)
        assert result["slides"][0]["variables"]["theme"] == "bold"

    def test_author_name_still_injected(self):
        outline = {
            "slides": [{"type": "hook", "variables": {"headline": "H"}}],
            "design": {"theme": "cool"},
        }
        result = _normalize_outline(outline)
        assert result["slides"][0]["variables"]["author_name"] == "Juan Camilo Martinez"
        assert result["slides"][0]["variables"]["theme"] == "cool"


class TestAutoSvgInjection:
    """Test _inject_auto_svg via _normalize_outline."""

    def test_stat_slide_gets_sparkline(self):
        outline = {
            "slides": [{"type": "stat", "variables": {"stat_value": "73%", "trend": "up"}}],
        }
        result = _normalize_outline(outline)
        assert "sparkline_svg" in result["slides"][0]["variables"]
        assert "<svg" in result["slides"][0]["variables"]["sparkline_svg"]

    def test_stat_slide_no_sparkline_if_provided(self):
        outline = {
            "slides": [{"type": "stat", "variables": {"stat_value": "73%", "sparkline_svg": "<svg>custom</svg>"}}],
        }
        result = _normalize_outline(outline)
        assert result["slides"][0]["variables"]["sparkline_svg"] == "<svg>custom</svg>"

    def test_split_slide_gets_decorative(self):
        outline = {
            "slides": [{"type": "split_left", "variables": {"title": "Test"}}],
        }
        result = _normalize_outline(outline)
        assert "graphic_svg" in result["slides"][0]["variables"]
        assert "<svg" in result["slides"][0]["variables"]["graphic_svg"]

    def test_split_slide_no_decorative_if_provided(self):
        outline = {
            "slides": [{"type": "split_right", "variables": {"graphic_svg": "<svg>mine</svg>"}}],
        }
        result = _normalize_outline(outline)
        assert result["slides"][0]["variables"]["graphic_svg"] == "<svg>mine</svg>"

    def test_body_slide_not_injected(self):
        outline = {
            "slides": [{"type": "body", "variables": {"title": "X"}}],
        }
        result = _normalize_outline(outline)
        assert "sparkline_svg" not in result["slides"][0]["variables"]
        assert "graphic_svg" not in result["slides"][0]["variables"]


class TestCarouselSpecToSlides:
    """Test carousel_spec_to_slides converter."""

    def _minimal_input(self) -> dict:
        return {
            "slides": [
                {"type": "hook", "variables": {"headline": "5 Tips for AI"}},
                {"type": "body", "variables": {"title": "Tip 1", "body": "Do this"}},
                {"type": "summary", "variables": {"title": "Recap", "takeaways": ["A", "B"]}},
                {"type": "cta", "variables": {"headline": "Follow me", "cta_text": "Subscribe"}},
            ]
        }

    def test_minimal_valid_input(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        assert isinstance(spec, CarouselSpec)
        assert len(spec.slides) == 4

    def test_slide_types_mapped_to_templates(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        assert spec.slides[0].template == "carousel/hook_slide"
        assert spec.slides[1].template == "carousel/body_slide"
        assert spec.slides[2].template == "carousel/summary_slide"
        assert spec.slides[3].template == "carousel/cta_slide"

    def test_slide_numbers_assigned_sequentially(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        for i, slide in enumerate(spec.slides, start=1):
            assert slide.slide_number == i

    def test_variables_preserved(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        assert spec.slides[0].variables["headline"] == "5 Tips for AI"
        assert spec.slides[1].variables["title"] == "Tip 1"
        assert spec.slides[2].variables["takeaways"] == ["A", "B"]
        assert spec.slides[3].variables["cta_text"] == "Subscribe"

    def test_default_viewport_4_5(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        assert spec.viewport_width == 1080
        assert spec.viewport_height == 1350

    def test_custom_viewport(self):
        spec = carousel_spec_to_slides(
            self._minimal_input(),
            viewport_width=1200,
            viewport_height=1500,
        )
        assert spec.viewport_width == 1200
        assert spec.viewport_height == 1500

    def test_pdf_output_format(self):
        spec = carousel_spec_to_slides(
            self._minimal_input(),
            output_format=OutputFormat.PDF,
        )
        assert spec.output_format == OutputFormat.PDF

    def test_default_output_format_png(self):
        spec = carousel_spec_to_slides(self._minimal_input())
        assert spec.output_format == OutputFormat.PNG

    def test_missing_slides_key_raises(self):
        with pytest.raises(ValueError, match="slides"):
            carousel_spec_to_slides({})

    def test_empty_slides_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            carousel_spec_to_slides({"slides": []})

    def test_slides_not_list_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            carousel_spec_to_slides({"slides": "not a list"})

    def test_unknown_slide_type_raises(self):
        data = {"slides": [{"type": "unknown_type", "variables": {}}]}
        with pytest.raises(ValueError, match="Unknown slide type"):
            carousel_spec_to_slides(data)

    def test_missing_type_defaults_to_body(self):
        data = {"slides": [{"variables": {"title": "Untitled"}}]}
        spec = carousel_spec_to_slides(data)
        assert spec.slides[0].template == "carousel/body_slide"

    def test_missing_variables_defaults_to_empty(self):
        data = {"slides": [{"type": "hook"}]}
        spec = carousel_spec_to_slides(data)
        assert spec.slides[0].variables == {}

    def test_single_slide_carousel(self):
        data = {"slides": [{"type": "hook", "variables": {"headline": "Solo"}}]}
        spec = carousel_spec_to_slides(data)
        assert len(spec.slides) == 1
        assert spec.slides[0].slide_number == 1

    def test_many_slides(self):
        slides = [{"type": "body", "variables": {"title": f"Slide {i}"}} for i in range(15)]
        data = {"slides": slides}
        spec = carousel_spec_to_slides(data)
        assert len(spec.slides) == 15
        assert spec.slides[14].slide_number == 15


# ---------------------------------------------------------------------------
# Summary slide template rendering
# ---------------------------------------------------------------------------


class TestSummarySlideTemplate:
    """Test the summary_slide.html.j2 template renders correctly."""

    def _make_engine(self) -> TemplateEngine:
        from pathlib import Path

        from holus.visual.brand import BrandVisualIdentityLoader

        loader = BrandVisualIdentityLoader(Path("/nonexistent/brand.yaml"))
        return TemplateEngine(brand_loader=loader)

    def test_render_summary_slide(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "title": "Key Takeaways",
            "takeaways": ["Point A", "Point B", "Point C"],
        })
        assert "Key Takeaways" in html
        assert "Point A" in html
        assert "Point B" in html
        assert "Point C" in html

    def test_summary_slide_has_numbered_items(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "takeaways": ["First", "Second"],
        })
        assert "summary-number" in html
        assert "summary-text" in html

    def test_summary_slide_default_title(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "takeaways": ["Item"],
        })
        assert "Key Takeaways" in html

    def test_summary_slide_with_label(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "label": "SUMMARY",
            "takeaways": ["Item"],
        })
        assert "SUMMARY" in html

    def test_summary_slide_with_author(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "takeaways": ["Item"],
            "author_name": "Camilo",
        })
        assert "Camilo" in html

    def test_summary_slide_empty_takeaways(self):
        """Renders without error even if takeaways is empty."""
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "title": "Nothing here",
            "takeaways": [],
        })
        assert "Nothing here" in html
        # No list items rendered (summary-text appears in CSS but not as HTML element content)
        assert "<li>" not in html

    def test_summary_slide_no_takeaways_key(self):
        """Renders without error if takeaways is not provided."""
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {
            "title": "Empty Summary",
        })
        assert "Empty Summary" in html


# ---------------------------------------------------------------------------
# Carousel CSS loading
# ---------------------------------------------------------------------------


class TestCarouselCssLoading:
    """Test that carousel templates load both slide.css and carousel.css."""

    def _make_engine(self) -> TemplateEngine:
        from pathlib import Path

        from holus.visual.brand import BrandVisualIdentityLoader

        loader = BrandVisualIdentityLoader(Path("/nonexistent/brand.yaml"))
        return TemplateEngine(brand_loader=loader)

    def test_carousel_loads_slide_css(self):
        engine = self._make_engine()
        html = engine.render("carousel/hook_slide", {"headline": "Test"})
        assert ".slide-container" in html

    def test_carousel_loads_carousel_css(self):
        engine = self._make_engine()
        html = engine.render("carousel/hook_slide", {"headline": "Test"})
        assert ".slide-summary" in html
        assert ".carousel-page-counter" in html

    def test_summary_slide_loads_carousel_css(self):
        engine = self._make_engine()
        html = engine.render("carousel/summary_slide", {"takeaways": ["A"]})
        assert ".carousel-page-counter" in html
        assert ".summary-list" in html


# ---------------------------------------------------------------------------
# render_carousel_pdf
# ---------------------------------------------------------------------------


class TestRenderCarouselPdf:
    """Test render_carousel_pdf method on PlaywrightEngine."""

    @pytest.fixture
    def mock_template_engine(self):
        engine = MagicMock(spec=TemplateEngine)
        engine.render.return_value = "<html><body>Slide</body></html>"
        return engine

    @pytest.fixture
    def mock_page(self):
        page = AsyncMock()
        page.set_content = AsyncMock()
        page.pdf = AsyncMock(return_value=b"CAROUSEL_PDF_BYTES")
        page.close = AsyncMock()
        return page

    @pytest.fixture
    def mock_browser(self, mock_page):
        browser = AsyncMock()
        browser.new_page = AsyncMock(return_value=mock_page)
        browser.close = AsyncMock()
        return browser

    @pytest.mark.asyncio
    async def test_success(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", variables={"headline": "H"}, slide_number=1),
                SlideSpec(template="carousel/body_slide", variables={"title": "B"}, slide_number=2),
            ],
        )
        # Mock _merge_pdfs since fake bytes aren't valid PDFs for pypdf
        with patch.object(PlaywrightEngine, "_merge_pdfs", return_value=b"MERGED_PDF"):
            result = await engine.render_carousel_pdf(spec)
        assert result.success is True
        assert result.output_bytes == b"MERGED_PDF"
        assert result.format == OutputFormat.PDF
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_uses_pixel_dimensions(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[SlideSpec(template="carousel/hook_slide", variables={}, slide_number=1)],
            viewport_width=1080,
            viewport_height=1350,
        )
        await engine.render_carousel_pdf(spec)
        # PDF should use pixel dimensions, not standard page sizes
        mock_page.pdf.assert_awaited_once()
        call_kwargs = mock_page.pdf.call_args[1]
        assert call_kwargs["width"] == "1080px"
        assert call_kwargs["height"] == "1350px"
        assert call_kwargs["print_background"] is True

    @pytest.mark.asyncio
    async def test_browser_not_started(self, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        spec = CarouselSpec(
            slides=[SlideSpec(template="carousel/hook_slide", variables={}, slide_number=1)],
        )
        result = await engine.render_carousel_pdf(spec)
        assert result.success is False
        assert "context manager" in result.error.lower()

    @pytest.mark.asyncio
    async def test_injects_slide_metadata(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", variables={"headline": "H"}, slide_number=1),
                SlideSpec(template="carousel/body_slide", variables={"title": "B"}, slide_number=2),
            ],
        )
        await engine.render_carousel_pdf(spec)
        # Verify template engine received slide_number and total_slides
        calls = mock_template_engine.render.call_args_list
        assert calls[0][0][1]["slide_number"] == 1
        assert calls[0][0][1]["total_slides"] == 2
        assert calls[1][0][1]["slide_number"] == 2
        assert calls[1][0][1]["total_slides"] == 2

    @pytest.mark.asyncio
    async def test_page_closed_after_render(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[SlideSpec(template="carousel/hook_slide", variables={}, slide_number=1)],
        )
        await engine.render_carousel_pdf(spec)
        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_page_closed_on_error(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser
        mock_page.pdf.side_effect = Exception("PDF generation failed")

        spec = CarouselSpec(
            slides=[SlideSpec(template="carousel/hook_slide", variables={}, slide_number=1)],
        )
        result = await engine.render_carousel_pdf(spec)
        assert result.success is False
        assert "PDF generation failed" in result.error
        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multi_slide_rendered_individually(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", variables={}, slide_number=1),
                SlideSpec(template="carousel/body_slide", variables={}, slide_number=2),
                SlideSpec(template="carousel/cta_slide", variables={}, slide_number=3),
            ],
        )
        # Mock _merge_pdfs since fake bytes aren't valid PDFs for pypdf
        with patch.object(PlaywrightEngine, "_merge_pdfs", return_value=b"MERGED") as merge_mock:
            result = await engine.render_carousel_pdf(spec)
        # Each slide rendered individually (3 set_content calls, 3 pdf calls)
        assert mock_page.set_content.await_count == 3
        assert mock_page.pdf.await_count == 3
        # _merge_pdfs called with 3 slide PDFs
        merge_mock.assert_called_once()
        assert len(merge_mock.call_args[0][0]) == 3
        assert result.success is True


# ---------------------------------------------------------------------------
# _combine_carousel_html static method
# ---------------------------------------------------------------------------


class TestCombineCarouselHtml:
    """Test the carousel-specific HTML combiner."""

    def test_single_page(self):
        result = PlaywrightEngine._combine_carousel_html(["<div>Page 1</div>"])
        assert "Page 1" in result
        assert "1080px" in result
        assert "1350px" in result
        assert "@page" in result

    def test_multiple_pages_have_breaks(self):
        result = PlaywrightEngine._combine_carousel_html([
            "<div>Page 1</div>",
            "<div>Page 2</div>",
        ])
        assert "page-break-before: always;" in result
        assert "Page 1" in result
        assert "Page 2" in result

    def test_custom_dimensions(self):
        result = PlaywrightEngine._combine_carousel_html(
            ["<div>Test</div>"],
            width=1200,
            height=1500,
        )
        assert "1200px" in result
        assert "1500px" in result

    def test_has_zero_margin_page_rule(self):
        result = PlaywrightEngine._combine_carousel_html(["<div>Test</div>"])
        assert "margin: 0" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCarouselEdgeCases:
    """Edge case tests for carousel pipeline."""

    def test_carousel_spec_to_slides_preserves_list_variables(self):
        data = {
            "slides": [
                {
                    "type": "summary",
                    "variables": {
                        "title": "Recap",
                        "takeaways": ["One", "Two", "Three"],
                    },
                }
            ]
        }
        spec = carousel_spec_to_slides(data)
        assert spec.slides[0].variables["takeaways"] == ["One", "Two", "Three"]

    def test_carousel_spec_to_slides_extra_fields_ignored(self):
        """Extra keys in carousel_output (like title) don't cause errors."""
        data = {
            "slides": [{"type": "hook", "variables": {"headline": "H"}}],
            "title": "My Carousel",
            "extra_field": "ignored",
        }
        spec = carousel_spec_to_slides(data)
        assert len(spec.slides) == 1

    def test_slide_with_empty_variables(self):
        data = {"slides": [{"type": "hook", "variables": {}}]}
        spec = carousel_spec_to_slides(data)
        assert spec.slides[0].variables == {}

    def test_new_slide_types_valid(self):
        """All 11 slide types can be used together."""
        data = {
            "slides": [
                {"type": t, "variables": {}}
                for t in [
                    "hook", "body", "summary", "cta",
                    "split_left", "split_right", "centered",
                    "quote", "stat", "comparison", "data",
                ]
            ]
        }
        spec = carousel_spec_to_slides(data)
        assert len(spec.slides) == 11

    def test_all_slide_types_valid(self):
        """All four slide types can be used together."""
        data = {
            "slides": [
                {"type": "hook", "variables": {}},
                {"type": "body", "variables": {}},
                {"type": "summary", "variables": {}},
                {"type": "cta", "variables": {}},
            ]
        }
        spec = carousel_spec_to_slides(data)
        assert len(spec.slides) == 4
        templates = [s.template for s in spec.slides]
        assert "carousel/hook_slide" in templates
        assert "carousel/body_slide" in templates
        assert "carousel/summary_slide" in templates
        assert "carousel/cta_slide" in templates
