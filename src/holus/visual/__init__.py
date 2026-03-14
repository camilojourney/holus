"""Visual rendering package for branded social media content.

Provides Playwright-based rendering of Jinja2 templates into PNG/PDF,
with brand identity injection from config/brand-visual.yaml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from holus.visual.brand import BrandVisualIdentityLoader
from holus.visual.engine import PlaywrightEngine
from holus.visual.models import (
    CarouselSpec,
    OutputFormat,
    PollSpec,
    RenderResult,
    RenderSpec,
    SlideSpec,
    VideoSkeletonSpec,
)
from holus.visual.spec_converter import (
    before_after_to_spec,
    carousel_spec_to_slides,
    data_viz_to_spec,
    insight_to_spec,
    poll_to_spec,
)
from holus.visual.templates import TemplateEngine

if TYPE_CHECKING:
    from holus.agents.marketing.models import BrandVisualIdentity


async def render_visual(
    spec: RenderSpec,
    brand_config: BrandVisualIdentity | None = None,
) -> bytes:
    """Convenience function: render a RenderSpec to image/PDF bytes.

    Loads brand config (from YAML or provided), creates a PlaywrightEngine,
    renders the spec, and returns raw bytes. Raises on render failure.

    Args:
        spec: The render specification (template + variables + format).
        brand_config: Optional brand visual identity. If None, loads from
            config/brand-visual.yaml via BrandVisualIdentityLoader.

    Returns:
        Raw bytes of the rendered image (PNG) or document (PDF).

    Raises:
        RuntimeError: If the render fails (browser error, template missing, etc.).
    """
    if brand_config is None:
        loader = BrandVisualIdentityLoader()
        brand_config = loader.load()

    template_engine = TemplateEngine(brand_loader=BrandVisualIdentityLoader())
    # Inject brand config into the loader used by the template engine
    template_engine._brand_loader._cached = brand_config

    async with PlaywrightEngine(template_engine=template_engine) as engine:
        result = await engine.render_spec(spec)

    if not result.success:
        msg = f"Render failed: {result.error}"
        raise RuntimeError(msg)

    if result.output_bytes is None:
        msg = "Render succeeded but produced no output bytes"
        raise RuntimeError(msg)

    return result.output_bytes


async def render_carousel_visual(
    spec: CarouselSpec,
    brand_config: BrandVisualIdentity | None = None,
) -> bytes:
    """Convenience function: render a CarouselSpec to a single PDF with all slides.

    Loads brand config (from YAML or provided), creates a PlaywrightEngine,
    renders all slides into a multi-page PDF, and returns raw bytes.

    Args:
        spec: The carousel specification (slides + format).
        brand_config: Optional brand visual identity. If None, loads from
            config/brand-visual.yaml via BrandVisualIdentityLoader.

    Returns:
        Raw bytes of the rendered carousel PDF.

    Raises:
        RuntimeError: If the render fails (browser error, template missing, etc.).
    """
    if brand_config is None:
        loader = BrandVisualIdentityLoader()
        brand_config = loader.load()

    template_engine = TemplateEngine(brand_loader=BrandVisualIdentityLoader())
    template_engine._brand_loader._cached = brand_config

    async with PlaywrightEngine(template_engine=template_engine) as engine:
        result = await engine.render_carousel_pdf(spec)

    if not result.success:
        msg = f"Carousel render failed: {result.error}"
        raise RuntimeError(msg)

    if result.output_bytes is None:
        msg = "Carousel render succeeded but produced no output bytes"
        raise RuntimeError(msg)

    return result.output_bytes


__all__ = [
    "BrandVisualIdentityLoader",
    "CarouselSpec",
    "OutputFormat",
    "PlaywrightEngine",
    "PollSpec",
    "RenderResult",
    "RenderSpec",
    "SlideSpec",
    "TemplateEngine",
    "VideoSkeletonSpec",
    "before_after_to_spec",
    "carousel_spec_to_slides",
    "data_viz_to_spec",
    "insight_to_spec",
    "poll_to_spec",
    "render_carousel_visual",
    "render_visual",
]
