"""End-to-end carousel rendering tests.

Exercises the FULL pipeline:
  LLM outline (mocked) → _normalize_outline → carousel_spec_to_slides
  → TemplateEngine.render → PlaywrightEngine → real PDF bytes

No API calls. Real Chromium rendering. Validates that every new slide type,
theme, gradient, font pairing, and visual effect produces non-zero output.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from holus.visual.carousel_builder import _normalize_outline, build_carousel_pdf
from holus.visual.engine import PlaywrightEngine
from holus.visual.spec_converter import carousel_spec_to_slides
from holus.visual.templates import TemplateEngine


def _make_outline(
    slide_types: list[dict],
    design: dict | None = None,
) -> dict:
    """Build a realistic carousel outline as idea_runner would produce."""
    return {
        "slides": slide_types,
        "design": design or {},
        "caption": "Test caption. Swipe →",
        "hook_score": "8",
        "voice_check": "PASS",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def template_engine():
    return TemplateEngine()


@pytest.fixture
def full_outline() -> dict:
    """A carousel using every new slide type + full design block."""
    return _make_outline(
        [
            {"type": "hook", "variables": {"headline": "Why AI Agents Fail", "subheadline": "And how to fix them"}},
            {"type": "body", "variables": {"title": "The Problem", "body": "Most agents lack feedback loops.", "bullet_points": ["→ No eval", "→ No memory", "→ No improvement"]}},
            {"type": "stat", "variables": {"stat_value": "73%", "stat_label": "of agents stall after week 1", "context": "Without self-improvement, agents plateau fast.", "trend": "down"}},
            {"type": "quote", "variables": {"quote_text": "The best agent is the one that improves itself.", "attribution": "Camilo Martinez", "attribution_title": "AI Engineer"}},
            {"type": "comparison", "variables": {"left_title": "Without Eval", "left_items": ["Blind deployments", "Silent failures", "No learning"], "right_title": "With Eval", "right_items": ["Scored outputs", "Auto-fix loops", "Continuous improvement"]}},
            {"type": "centered", "variables": {"text": "Build the loop first.", "subtext": "Everything else follows."}},
            {"type": "split_left", "variables": {"title": "The Architecture", "body": "Observe → Reason → Act → Evaluate", "bullet_points": ["→ ReAct pattern", "→ Domain judges"]}},
            {"type": "summary", "variables": {"title": "Key Takeaways", "items": ["Eval gates catch regressions", "Memory compounds quality", "Self-improvement is the moat"]}},
            {"type": "cta", "variables": {"headline": "What feedback loop does your agent have?"}},
        ],
        design={
            "theme": "dark",
            "font_pairing": "tech",
            "gradient": "indigo_mesh",
            "effect": "glass",
        },
    )


# ---------------------------------------------------------------------------
# Tests — real Playwright rendering
# ---------------------------------------------------------------------------


class TestCarouselE2E:
    """Full pipeline tests with real browser rendering."""

    @pytest.mark.asyncio
    async def test_full_carousel_renders_pdf(self, full_outline, tmp_path):
        """Complete pipeline: outline → normalize → spec → render → PDF bytes."""
        normalized = _normalize_outline(full_outline)
        spec = carousel_spec_to_slides(normalized)

        engine = TemplateEngine()
        async with PlaywrightEngine(template_engine=engine) as pw:
            result = await pw.render_carousel_pdf(spec)

        assert result.success, f"Render failed: {result.error}"
        assert len(result.output_bytes) > 1000, "PDF too small — likely empty"

        # Write to disk and verify it's a valid PDF
        pdf_path = tmp_path / "test_carousel.pdf"
        pdf_path.write_bytes(result.output_bytes)
        assert pdf_path.stat().st_size > 1000
        assert result.output_bytes[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_each_theme_renders(self, tmp_path):
        """Each of the 5 themes produces a valid PDF."""
        for theme in ("dark", "light", "warm", "cool", "bold"):
            outline = _make_outline(
                [
                    {"type": "hook", "variables": {"headline": f"Theme: {theme}"}},
                    {"type": "body", "variables": {"title": "Test", "body": "Content"}},
                    {"type": "cta", "variables": {"headline": "Question?"}},
                ],
                design={"theme": theme},
            )
            normalized = _normalize_outline(outline)
            spec = carousel_spec_to_slides(normalized)

            engine = TemplateEngine()
            async with PlaywrightEngine(template_engine=engine) as pw:
                result = await pw.render_carousel_pdf(spec)

            assert result.success, f"Theme '{theme}' failed: {result.error}"
            assert len(result.output_bytes) > 500

    @pytest.mark.asyncio
    async def test_each_effect_renders(self, tmp_path):
        """Each visual effect produces a valid render."""
        for effect in ("none", "glass", "neubrutalism", "depth", "glow", "grain"):
            outline = _make_outline(
                [
                    {"type": "hook", "variables": {"headline": f"Effect: {effect}"}},
                    {"type": "cta", "variables": {"headline": "Done"}},
                ],
                design={"effect": effect},
            )
            normalized = _normalize_outline(outline)
            spec = carousel_spec_to_slides(normalized)

            engine = TemplateEngine()
            async with PlaywrightEngine(template_engine=engine) as pw:
                result = await pw.render_carousel_pdf(spec)

            assert result.success, f"Effect '{effect}' failed: {result.error}"

    @pytest.mark.asyncio
    async def test_each_font_pairing_renders(self, tmp_path):
        """Each font pairing produces a valid render."""
        for fp in ("tech", "editorial", "modern", "bold"):
            outline = _make_outline(
                [
                    {"type": "hook", "variables": {"headline": f"Fonts: {fp}"}},
                    {"type": "cta", "variables": {"headline": "End"}},
                ],
                design={"font_pairing": fp},
            )
            normalized = _normalize_outline(outline)
            spec = carousel_spec_to_slides(normalized)

            engine = TemplateEngine()
            async with PlaywrightEngine(template_engine=engine) as pw:
                result = await pw.render_carousel_pdf(spec)

            assert result.success, f"Font pairing '{fp}' failed: {result.error}"

    @pytest.mark.asyncio
    async def test_each_gradient_renders(self, tmp_path):
        """Each gradient preset produces a valid render."""
        for grad in ("dark_navy", "indigo_mesh", "warm_sunset", "cool_ocean", "bold_fire", "frosted_glass", "aurora", "minimal_light"):
            outline = _make_outline(
                [
                    {"type": "hook", "variables": {"headline": f"Grad: {grad}"}},
                    {"type": "cta", "variables": {"headline": "End"}},
                ],
                design={"gradient": grad},
            )
            normalized = _normalize_outline(outline)
            spec = carousel_spec_to_slides(normalized)

            engine = TemplateEngine()
            async with PlaywrightEngine(template_engine=engine) as pw:
                result = await pw.render_carousel_pdf(spec)

            assert result.success, f"Gradient '{grad}' failed: {result.error}"

    @pytest.mark.asyncio
    async def test_build_carousel_pdf_async(self, full_outline, tmp_path):
        """The async _render path works end-to-end to produce a real PDF."""
        from holus.visual.carousel_builder import _render

        pdf_path = tmp_path / "async_test.pdf"
        result_path = await _render(full_outline, pdf_path)
        assert result_path == pdf_path
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 1000
        assert pdf_path.read_bytes()[:5] == b"%PDF-"
