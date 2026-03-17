"""Carousel PDF builder — converts carousel outline JSON to a rendered PDF.

Takes the JSON produced by idea_runner.py (carousel_outline format) and renders
it to a multi-page PDF using the Playwright engine + Jinja2 slide templates.

Usage::

    from holus.visual.carousel_builder import build_carousel_pdf

    # outline is the dict returned by generate_piece() for carousel_outline
    pdf_path = build_carousel_pdf(outline, output_path=Path("data/content-queue/my-carousel.pdf"))
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from holus.visual.engine import PlaywrightEngine
from holus.visual.models import OutputFormat
from holus.visual.spec_converter import carousel_spec_to_slides
from holus.visual.templates import TemplateEngine

logger = logging.getLogger(__name__)


def _normalize_outline(outline: dict[str, Any]) -> dict[str, Any]:
    """Normalize idea_runner carousel output to carousel_spec_to_slides() format.

    idea_runner returns {"slides": [...], "caption": "...", "design": {...}, ...}
    spec_converter expects {"slides": [{"type": "...", "variables": {...}}]}

    Extracts the top-level ``design`` block and merges its fields into every
    slide's variables so the template engine can resolve theme, font_pairing,
    background_gradient, and visual_effect.
    """
    slides = outline.get("slides", [])
    if not slides:
        msg = "carousel outline has no slides"
        raise ValueError(msg)

    # Extract carousel-level design decisions
    design = outline.get("design", {})
    design_vars: dict[str, str] = {}
    if isinstance(design, dict):
        if design.get("theme"):
            design_vars["theme"] = design["theme"]
        if design.get("font_pairing"):
            design_vars["font_pairing"] = design["font_pairing"]
        if design.get("gradient"):
            design_vars["background_gradient"] = design["gradient"]
        if design.get("effect") and design["effect"] != "none":
            design_vars["visual_effect"] = design["effect"]

    normalized: list[dict[str, Any]] = []
    for slide in slides:
        slide_type = slide.get("type", "body")
        variables = dict(slide.get("variables", {}))

        # Inject author name into hook and footer slides
        if slide_type in ("hook", "cta") and "author_name" not in variables:
            variables["author_name"] = ""

        # Merge design decisions (slide-level overrides win)
        for key, value in design_vars.items():
            if key not in variables:
                variables[key] = value

        normalized.append({"type": slide_type, "variables": variables})

    return {"slides": normalized}


async def _render(outline: dict[str, Any], output_path: Path) -> Path:
    template_engine = TemplateEngine()
    spec = carousel_spec_to_slides(
        _normalize_outline(outline),
        output_format=OutputFormat.PDF,
        viewport_width=1080,
        viewport_height=1350,
    )

    async with PlaywrightEngine(template_engine=template_engine) as engine:
        result = await engine.render_carousel_pdf(spec)

    if not result.success:
        msg = f"Carousel render failed: {result.error}"
        raise RuntimeError(msg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.output_bytes)
    logger.info("Carousel PDF saved: %s (%d bytes)", output_path, len(result.output_bytes))
    return output_path


def build_carousel_pdf(outline: dict[str, Any], output_path: Path) -> Path:
    """Render a carousel outline to a PDF file.

    Args:
        outline: Dict from generate_piece() with format=carousel_outline.
                 Must contain a "slides" list with type + variables per slide.
        output_path: Where to write the PDF. Parent dirs are created if needed.

    Returns:
        The output_path after the file has been written.

    Raises:
        ValueError: If the outline has no slides or an unknown slide type.
        RuntimeError: If the Playwright render fails.
    """
    return asyncio.run(_render(outline, output_path))
