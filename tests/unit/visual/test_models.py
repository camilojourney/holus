"""Tests for visual rendering models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from holus.visual.models import (
    CarouselSpec,
    OutputFormat,
    RenderResult,
    RenderSpec,
    SlideSpec,
)


class TestRenderSpec:
    """Test RenderSpec model."""

    def test_defaults(self):
        spec = RenderSpec(template="single_image/insight")
        assert spec.output_format == OutputFormat.PNG
        assert spec.viewport_width == 1080
        assert spec.viewport_height == 1080
        assert spec.timeout_ms == 30_000
        assert spec.variables == {}

    def test_custom_values(self):
        spec = RenderSpec(
            template="carousel/hook_slide",
            variables={"headline": "Test"},
            output_format=OutputFormat.PDF,
            viewport_width=1920,
            viewport_height=1080,
            timeout_ms=60_000,
        )
        assert spec.template == "carousel/hook_slide"
        assert spec.variables["headline"] == "Test"
        assert spec.output_format == OutputFormat.PDF

    def test_viewport_minimum(self):
        with pytest.raises(ValidationError):
            RenderSpec(template="test", viewport_width=50)

    def test_timeout_bounds(self):
        with pytest.raises(ValidationError):
            RenderSpec(template="test", timeout_ms=500)
        with pytest.raises(ValidationError):
            RenderSpec(template="test", timeout_ms=200_000)


class TestSlideSpec:
    """Test SlideSpec model."""

    def test_valid_slide(self):
        slide = SlideSpec(
            template="carousel/hook_slide",
            variables={"headline": "Hello"},
            slide_number=1,
        )
        assert slide.slide_number == 1
        assert slide.variables["headline"] == "Hello"

    def test_slide_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            SlideSpec(template="test", slide_number=0)


class TestCarouselSpec:
    """Test CarouselSpec model."""

    def test_valid_carousel(self):
        spec = CarouselSpec(
            slides=[
                SlideSpec(template="carousel/hook_slide", slide_number=1),
                SlideSpec(template="carousel/body_slide", slide_number=2),
                SlideSpec(template="carousel/cta_slide", slide_number=3),
            ],
        )
        assert len(spec.slides) == 3
        assert spec.viewport_width == 1080
        assert spec.viewport_height == 1350

    def test_empty_slides_rejected(self):
        with pytest.raises(ValidationError):
            CarouselSpec(slides=[])

    def test_custom_dimensions(self):
        spec = CarouselSpec(
            slides=[SlideSpec(template="t", slide_number=1)],
            viewport_width=1920,
            viewport_height=1080,
        )
        assert spec.viewport_width == 1920


class TestRenderResult:
    """Test RenderResult model."""

    def test_success_result(self):
        result = RenderResult(
            success=True,
            output_bytes=b"PNG_DATA",
            duration_ms=150,
            format=OutputFormat.PNG,
        )
        assert result.success is True
        assert result.output_bytes == b"PNG_DATA"
        assert result.error is None

    def test_failure_result(self):
        result = RenderResult(
            success=False,
            error="Browser timeout",
            duration_ms=30_000,
            format=OutputFormat.PNG,
        )
        assert result.success is False
        assert result.output_bytes is None
        assert result.error == "Browser timeout"

    def test_rendered_at_auto_set(self):
        result = RenderResult(success=True)
        assert result.rendered_at is not None

    def test_pdf_format(self):
        result = RenderResult(success=True, format=OutputFormat.PDF)
        assert result.format == OutputFormat.PDF


class TestOutputFormat:
    """Test OutputFormat enum."""

    def test_values(self):
        assert OutputFormat.PNG == "png"
        assert OutputFormat.PDF == "pdf"
