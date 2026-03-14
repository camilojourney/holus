"""Pydantic models for the visual rendering pipeline.

RenderSpec describes what to render. RenderResult describes the outcome.
SlideSpec / CarouselSpec describe carousel-specific inputs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    """Supported output formats."""

    PNG = "png"
    PDF = "pdf"


class RenderSpec(BaseModel):
    """Specification for a single render job."""

    template: str = Field(description="Template path relative to templates/ dir, e.g. 'single_image/insight'")
    variables: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict, description="Template variables"
    )
    output_format: OutputFormat = Field(default=OutputFormat.PNG, description="Output format")
    viewport_width: int = Field(default=1080, ge=100, description="Viewport width in px")
    viewport_height: int = Field(default=1080, ge=100, description="Viewport height in px")
    timeout_ms: int = Field(default=30_000, ge=1000, le=120_000, description="Render timeout in ms")


class SlideSpec(BaseModel):
    """Specification for a single carousel slide."""

    template: str = Field(description="Slide template name, e.g. 'carousel/hook_slide'")
    variables: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict, description="Slide-specific template variables"
    )
    slide_number: int = Field(ge=1, description="Position in the carousel (1-indexed)")


class CarouselSpec(BaseModel):
    """Specification for a complete carousel (multi-slide render)."""

    slides: list[SlideSpec] = Field(min_length=1, description="Ordered list of slides")
    viewport_width: int = Field(default=1080, ge=100, description="Slide width in px")
    viewport_height: int = Field(default=1350, ge=100, description="Slide height in px (4:5 aspect)")
    output_format: OutputFormat = Field(default=OutputFormat.PNG, description="Per-slide output format")
    timeout_ms: int = Field(default=30_000, ge=1000, le=120_000, description="Per-slide render timeout")


class RenderResult(BaseModel):
    """Outcome of a render operation."""

    success: bool = Field(description="Whether the render completed without error")
    output_bytes: bytes | None = Field(default=None, description="Rendered content bytes (PNG or PDF)")
    duration_ms: int = Field(default=0, ge=0, description="Render duration in ms")
    error: str | None = Field(default=None, description="Error message if success=False")
    rendered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp of render"
    )
    format: OutputFormat = Field(default=OutputFormat.PNG, description="Output format used")
