"""Playwright-based rendering engine for HTML → PNG/PDF.

Uses an async context manager for browser lifecycle management with reuse
and timeout protection. Designed for social media image generation.

Reference pattern: job-tracker/scripts/job_search/document_renderer.py
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

from holus.visual.models import (
    CarouselSpec,
    OutputFormat,
    RenderResult,
    RenderSpec,
)
from holus.visual.templates import TemplateEngine


class PlaywrightEngine:
    """Playwright-based renderer with browser reuse and timeout protection.

    Usage::

        async with PlaywrightEngine() as engine:
            result = await engine.render_png(html, viewport=(1080, 1080))
            pdf_bytes = await engine.render_pdf([page1_html, page2_html])

    The browser instance is reused across renders within the same context
    manager block. A new page is created per render and closed afterward.
    """

    def __init__(self, template_engine: TemplateEngine | None = None) -> None:
        self._template_engine = template_engine or TemplateEngine()
        self._playwright: object | None = None
        self._browser: object | None = None

    async def __aenter__(self) -> PlaywrightEngine:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)  # type: ignore[union-attr]
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._browser is not None:
            await self._browser.close()  # type: ignore[union-attr]
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()  # type: ignore[union-attr]
            self._playwright = None

    async def render_png(
        self,
        html: str,
        viewport: tuple[int, int] = (1080, 1080),
        timeout_ms: int = 30_000,
    ) -> RenderResult:
        """Render HTML to PNG bytes.

        Args:
            html: Complete HTML string to render.
            viewport: (width, height) tuple for the browser viewport.
            timeout_ms: Maximum time in ms before the render is aborted.

        Returns:
            RenderResult with output_bytes set to PNG data on success.
        """
        if self._browser is None:
            return RenderResult(
                success=False,
                error="Browser not started. Use 'async with PlaywrightEngine()' context manager.",
                format=OutputFormat.PNG,
            )

        started = time.perf_counter()
        try:
            page = await self._browser.new_page(  # type: ignore[union-attr]
                viewport={"width": viewport[0], "height": viewport[1]},
            )
            try:
                await page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
                screenshot_bytes = await page.screenshot(
                    full_page=False,
                    type="png",
                    timeout=timeout_ms,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                return RenderResult(
                    success=True,
                    output_bytes=screenshot_bytes,
                    duration_ms=duration_ms,
                    format=OutputFormat.PNG,
                )
            finally:
                await page.close()
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return RenderResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
                format=OutputFormat.PNG,
            )

    async def render_pdf(
        self,
        html_pages: list[str],
        page_size: str = "Letter",
        timeout_ms: int = 30_000,
    ) -> RenderResult:
        """Render one or more HTML pages to a single PDF.

        Args:
            html_pages: List of HTML strings, one per page.
            page_size: PDF page size (e.g., "Letter", "A4").
            timeout_ms: Maximum render time per page in ms.

        Returns:
            RenderResult with output_bytes set to PDF data on success.
        """
        if self._browser is None:
            return RenderResult(
                success=False,
                error="Browser not started. Use 'async with PlaywrightEngine()' context manager.",
                format=OutputFormat.PDF,
            )

        if not html_pages:
            return RenderResult(
                success=False,
                error="No HTML pages provided.",
                format=OutputFormat.PDF,
            )

        started = time.perf_counter()
        try:
            # For single page, render directly
            # For multiple pages, combine into one HTML with page breaks
            combined_html = self._combine_html_pages(html_pages)

            page = await self._browser.new_page()  # type: ignore[union-attr]
            try:
                await page.set_content(combined_html, wait_until="networkidle", timeout=timeout_ms)
                pdf_bytes = await page.pdf(
                    format=page_size,
                    print_background=True,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                return RenderResult(
                    success=True,
                    output_bytes=pdf_bytes,
                    duration_ms=duration_ms,
                    format=OutputFormat.PDF,
                )
            finally:
                await page.close()
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return RenderResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
                format=OutputFormat.PDF,
            )

    async def render_spec(self, spec: RenderSpec) -> RenderResult:
        """Render from a RenderSpec, using the template engine.

        Args:
            spec: Complete render specification.

        Returns:
            RenderResult from the render.
        """
        html = self._template_engine.render(spec.template, spec.variables)

        if spec.output_format == OutputFormat.PDF:
            return await self.render_pdf(
                [html],
                timeout_ms=spec.timeout_ms,
            )
        return await self.render_png(
            html,
            viewport=(spec.viewport_width, spec.viewport_height),
            timeout_ms=spec.timeout_ms,
        )

    async def render_carousel(self, spec: CarouselSpec) -> list[RenderResult]:
        """Render all slides of a carousel spec.

        Args:
            spec: Carousel specification with ordered slides.

        Returns:
            List of RenderResult, one per slide, in order.
        """
        results: list[RenderResult] = []
        for slide in spec.slides:
            # Add slide metadata to variables
            slide_vars = {
                **slide.variables,
                "slide_number": slide.slide_number,
                "total_slides": len(spec.slides),
            }
            html = self._template_engine.render(slide.template, slide_vars)

            if spec.output_format == OutputFormat.PDF:
                result = await self.render_pdf([html], timeout_ms=spec.timeout_ms)
            else:
                result = await self.render_png(
                    html,
                    viewport=(spec.viewport_width, spec.viewport_height),
                    timeout_ms=spec.timeout_ms,
                )
            results.append(result)
        return results

    async def render_carousel_pdf(self, spec: CarouselSpec) -> RenderResult:
        """Render all slides of a carousel as a single multi-page PDF.

        Each slide becomes a separate 1080x1350 page in the PDF document,
        suitable for LinkedIn carousel (document) uploads.

        Args:
            spec: Carousel specification with ordered slides.

        Returns:
            RenderResult with PDF bytes containing all slides as pages.
        """
        if self._browser is None:
            return RenderResult(
                success=False,
                error="Browser not started. Use 'async with PlaywrightEngine()' context manager.",
                format=OutputFormat.PDF,
            )

        if not spec.slides:
            return RenderResult(
                success=False,
                error="No slides provided.",
                format=OutputFormat.PDF,
            )

        started = time.perf_counter()
        try:
            # Render each slide to HTML
            html_pages: list[str] = []
            for slide in spec.slides:
                slide_vars = {
                    **slide.variables,
                    "slide_number": slide.slide_number,
                    "total_slides": len(spec.slides),
                }
                html = self._template_engine.render(slide.template, slide_vars)
                html_pages.append(html)

            # Combine into a single multi-page PDF
            combined_html = self._combine_carousel_html(
                html_pages,
                width=spec.viewport_width,
                height=spec.viewport_height,
            )

            page = await self._browser.new_page()  # type: ignore[union-attr]
            try:
                await page.set_content(
                    combined_html,
                    wait_until="networkidle",
                    timeout=spec.timeout_ms,
                )
                pdf_bytes = await page.pdf(
                    width=f"{spec.viewport_width}px",
                    height=f"{spec.viewport_height}px",
                    print_background=True,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                return RenderResult(
                    success=True,
                    output_bytes=pdf_bytes,
                    duration_ms=duration_ms,
                    format=OutputFormat.PDF,
                )
            finally:
                await page.close()
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return RenderResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
                format=OutputFormat.PDF,
            )

    @staticmethod
    def _combine_carousel_html(
        pages: list[str],
        width: int = 1080,
        height: int = 1350,
    ) -> str:
        """Combine multiple carousel slide HTML pages for PDF rendering.

        Each page is wrapped in a fixed-dimension div with CSS page-break rules
        so the PDF renderer produces one page per slide at the correct dimensions.
        """
        sections: list[str] = []
        for i, page_html in enumerate(pages):
            break_style = "page-break-before: always;" if i > 0 else ""
            sections.append(
                f'<div class="carousel-pdf-page" style="'
                f"width: {width}px; height: {height}px; "
                f"overflow: hidden; {break_style}"
                f'">{page_html}</div>'
            )

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
  size: {width}px {height}px;
  margin: 0;
}}
body {{
  margin: 0;
  padding: 0;
}}
.carousel-pdf-page {{
  page-break-after: always;
}}
.carousel-pdf-page:last-child {{
  page-break-after: auto;
}}
</style>
</head>
<body>
{"".join(sections)}
</body>
</html>"""

    @staticmethod
    def _combine_html_pages(pages: list[str]) -> str:
        """Combine multiple HTML pages with CSS page breaks for PDF rendering."""
        if len(pages) == 1:
            return pages[0]

        # Extract body contents and combine with page breaks
        sections: list[str] = []
        for i, page_html in enumerate(pages):
            style = 'style="page-break-before: always;"' if i > 0 else ""
            sections.append(f'<div class="pdf-page" {style}>{page_html}</div>')

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
.pdf-page {{ page-break-after: always; }}
.pdf-page:last-child {{ page-break-after: auto; }}
</style>
</head>
<body>
{"".join(sections)}
</body>
</html>"""
