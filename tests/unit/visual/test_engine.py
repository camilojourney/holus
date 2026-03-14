"""Tests for PlaywrightEngine with mocked Playwright.

Uses unittest.mock to avoid requiring a real browser installation during unit tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.visual.engine import PlaywrightEngine
from holus.visual.models import (
    CarouselSpec,
    OutputFormat,
    RenderSpec,
    SlideSpec,
)
from holus.visual.templates import TemplateEngine


@pytest.fixture
def mock_template_engine():
    """Mock template engine that returns simple HTML."""
    engine = MagicMock(spec=TemplateEngine)
    engine.render.return_value = "<html><body>Test</body></html>"
    return engine


@pytest.fixture
def mock_page():
    """Mock Playwright page."""
    page = AsyncMock()
    page.set_content = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"PNG_BYTES")
    page.pdf = AsyncMock(return_value=b"PDF_BYTES")
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_browser(mock_page):
    """Mock Playwright browser."""
    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=mock_page)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    """Mock Playwright context manager."""
    pw = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=mock_browser)
    pw.stop = AsyncMock()
    return pw


class TestPlaywrightEngineContextManager:
    """Test async context manager lifecycle."""

    @pytest.mark.asyncio
    async def test_enter_starts_browser(self, mock_playwright, mock_browser, mock_template_engine):
        with patch("playwright.async_api.async_playwright") as mock_async_pw:
            mock_cm = AsyncMock()
            mock_cm.start = AsyncMock(return_value=mock_playwright)
            mock_async_pw.return_value = mock_cm

            engine = PlaywrightEngine(mock_template_engine)
            result = await engine.__aenter__()
            assert result is engine
            assert engine._browser is mock_browser

    @pytest.mark.asyncio
    async def test_exit_closes_browser(self, mock_playwright, mock_browser, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._playwright = mock_playwright
        engine._browser = mock_browser

        await engine.__aexit__(None, None, None)
        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()
        assert engine._browser is None
        assert engine._playwright is None


class TestRenderPng:
    """Test PNG rendering."""

    @pytest.mark.asyncio
    async def test_success(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        result = await engine.render_png("<html>Test</html>", viewport=(1080, 1080))
        assert result.success is True
        assert result.output_bytes == b"PNG_BYTES"
        assert result.format == OutputFormat.PNG
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_custom_viewport(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        await engine.render_png("<html>Test</html>", viewport=(1920, 1080))
        mock_browser.new_page.assert_awaited_once_with(
            viewport={"width": 1920, "height": 1080},
        )

    @pytest.mark.asyncio
    async def test_browser_not_started(self, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        # _browser is None
        result = await engine.render_png("<html>Test</html>")
        assert result.success is False
        assert "context manager" in result.error.lower()

    @pytest.mark.asyncio
    async def test_render_error(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser
        mock_page.screenshot.side_effect = Exception("Screenshot failed")

        result = await engine.render_png("<html>Test</html>")
        assert result.success is False
        assert "Screenshot failed" in result.error

    @pytest.mark.asyncio
    async def test_page_closed_after_render(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        await engine.render_png("<html>Test</html>")
        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_page_closed_on_error(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser
        mock_page.set_content.side_effect = Exception("Load failed")

        result = await engine.render_png("<html>Test</html>")
        assert result.success is False
        mock_page.close.assert_awaited_once()


class TestRenderPdf:
    """Test PDF rendering."""

    @pytest.mark.asyncio
    async def test_success(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        result = await engine.render_pdf(["<html>Page 1</html>"])
        assert result.success is True
        assert result.output_bytes == b"PDF_BYTES"
        assert result.format == OutputFormat.PDF

    @pytest.mark.asyncio
    async def test_empty_pages_rejected(self, mock_browser, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        result = await engine.render_pdf([])
        assert result.success is False
        assert "No HTML pages" in result.error

    @pytest.mark.asyncio
    async def test_browser_not_started(self, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        result = await engine.render_pdf(["<html>Test</html>"])
        assert result.success is False

    @pytest.mark.asyncio
    async def test_multiple_pages_combined(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        result = await engine.render_pdf([
            "<html>Page 1</html>",
            "<html>Page 2</html>",
        ])
        assert result.success is True
        # Verify set_content was called with combined HTML
        call_args = mock_page.set_content.call_args
        combined_html = call_args[0][0]
        assert "page-break" in combined_html


class TestRenderSpec:
    """Test rendering from RenderSpec."""

    @pytest.mark.asyncio
    async def test_png_spec(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = RenderSpec(
            template="single_image/insight",
            variables={"headline": "Test"},
            output_format=OutputFormat.PNG,
            viewport_width=1080,
            viewport_height=1080,
        )
        result = await engine.render_spec(spec)
        assert result.success is True
        assert result.format == OutputFormat.PNG
        mock_template_engine.render.assert_called_once_with(
            "single_image/insight", {"headline": "Test"}
        )

    @pytest.mark.asyncio
    async def test_pdf_spec(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = RenderSpec(
            template="single_image/insight",
            variables={"headline": "Test"},
            output_format=OutputFormat.PDF,
        )
        result = await engine.render_spec(spec)
        assert result.success is True
        assert result.format == OutputFormat.PDF


class TestRenderCarousel:
    """Test carousel rendering."""

    @pytest.mark.asyncio
    async def test_three_slides(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", variables={"headline": "H"}, slide_number=1),
                SlideSpec(template="carousel/body_slide", variables={"title": "B"}, slide_number=2),
                SlideSpec(template="carousel/cta_slide", variables={"cta_text": "C"}, slide_number=3),
            ],
        )
        results = await engine.render_carousel(spec)
        assert len(results) == 3
        assert all(r.success for r in results)
        # Template engine called 3 times with augmented variables
        assert mock_template_engine.render.call_count == 3

    @pytest.mark.asyncio
    async def test_slide_metadata_injected(self, mock_browser, mock_page, mock_template_engine):
        engine = PlaywrightEngine(mock_template_engine)
        engine._browser = mock_browser

        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", variables={"headline": "H"}, slide_number=1),
                SlideSpec(template="carousel/body_slide", variables={"title": "B"}, slide_number=2),
            ],
        )
        await engine.render_carousel(spec)
        # Check that slide_number and total_slides were injected
        call_args_list = mock_template_engine.render.call_args_list
        first_call_vars = call_args_list[0][0][1]
        assert first_call_vars["slide_number"] == 1
        assert first_call_vars["total_slides"] == 2
        second_call_vars = call_args_list[1][0][1]
        assert second_call_vars["slide_number"] == 2
        assert second_call_vars["total_slides"] == 2


class TestCombineHtmlPages:
    """Test the static HTML page combiner."""

    def test_single_page_passthrough(self):
        result = PlaywrightEngine._combine_html_pages(["<html>Single</html>"])
        assert result == "<html>Single</html>"

    def test_multiple_pages_have_page_breaks(self):
        result = PlaywrightEngine._combine_html_pages([
            "<div>Page 1</div>",
            "<div>Page 2</div>",
        ])
        assert "page-break-before: always;" in result
        assert "Page 1" in result
        assert "Page 2" in result
        assert "<!DOCTYPE html>" in result
