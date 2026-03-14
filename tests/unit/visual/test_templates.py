"""Tests for the Jinja2 template engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from holus.agents.marketing.models import BrandVisualIdentity
from holus.visual.brand import BrandVisualIdentityLoader
from holus.visual.templates import TemplateEngine


class TestTemplateEngine:
    """Test template loading, rendering, and brand CSS injection."""

    def _make_engine(
        self,
        templates_dir: Path | None = None,
        styles_dir: Path | None = None,
    ) -> TemplateEngine:
        """Create a TemplateEngine with optional overrides."""
        loader = BrandVisualIdentityLoader(Path("/nonexistent/brand.yaml"))
        return TemplateEngine(
            templates_dir=templates_dir,
            styles_dir=styles_dir,
            brand_loader=loader,
        )

    def test_render_insight_template(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {
            "headline": "Test Headline",
            "body": "Test body text",
        })
        assert "Test Headline" in html
        assert "Test body text" in html
        assert "--brand-color-primary" in html  # brand CSS injected
        assert "<!DOCTYPE html>" in html

    def test_render_hook_slide(self):
        engine = self._make_engine()
        html = engine.render("carousel/hook_slide", {
            "headline": "Hook Title",
            "subheadline": "Subtitle here",
        })
        assert "Hook Title" in html
        assert "Subtitle here" in html
        assert "--brand-color-primary" in html

    def test_render_body_slide(self):
        engine = self._make_engine()
        html = engine.render("carousel/body_slide", {
            "title": "Body Title",
            "body": "Body content here",
        })
        assert "Body Title" in html
        assert "Body content here" in html

    def test_render_cta_slide(self):
        engine = self._make_engine()
        html = engine.render("carousel/cta_slide", {
            "headline": "Follow me!",
            "cta_text": "Subscribe Now",
        })
        assert "Follow me!" in html
        assert "Subscribe Now" in html

    def test_brand_css_injection(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {"headline": "Test"})
        # Default brand CSS variables should be present
        assert "--brand-color-primary: #E85D04;" in html
        assert "--brand-font-primary" in html

    def test_base_css_loaded_for_single_image(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {"headline": "Test"})
        # base.css content should be embedded
        assert "box-sizing: border-box" in html

    def test_slide_css_loaded_for_carousel(self):
        engine = self._make_engine()
        html = engine.render("carousel/hook_slide", {"headline": "Test"})
        # slide.css content should be embedded
        assert ".slide-container" in html

    def test_single_css_loaded_for_single_image(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {"headline": "Test"})
        # single.css content should be embedded
        assert ".single-container" in html

    def test_list_templates(self):
        engine = self._make_engine()
        templates = engine.list_templates()
        assert "single_image/insight" in templates
        assert "carousel/hook_slide" in templates
        assert "carousel/body_slide" in templates
        assert "carousel/cta_slide" in templates
        # base.html.j2 is a layout, not a standalone template — it should be listed
        assert "base" in templates

    def test_custom_brand_loader(self, tmp_path: Path):
        """Test that a custom brand loader injects different CSS."""
        mock_loader = MagicMock(spec=BrandVisualIdentityLoader)
        custom_brand = BrandVisualIdentity()
        custom_brand.colors.primary = "#AABBCC"  # type: ignore[misc]
        mock_loader.load.return_value = custom_brand

        engine = TemplateEngine(brand_loader=mock_loader)
        html = engine.render("single_image/insight", {"headline": "Test"})
        assert "--brand-color-primary: #AABBCC;" in html

    def test_render_with_stat_variables(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {
            "headline": "Revenue",
            "stat_value": "$1.2M",
            "stat_label": "Annual Revenue",
        })
        assert "$1.2M" in html
        assert "Annual Revenue" in html

    def test_render_with_quote_variables(self):
        engine = self._make_engine()
        html = engine.render("single_image/insight", {
            "headline": "Wisdom",
            "quote": "The best time to plant a tree was 20 years ago.",
            "quote_author": "Chinese Proverb",
        })
        assert "The best time to plant a tree was 20 years ago." in html
        assert "Chinese Proverb" in html

    def test_render_body_slide_with_bullets(self):
        engine = self._make_engine()
        html = engine.render("carousel/body_slide", {
            "title": "Key Points",
            "bullet_points": ["First point", "Second point", "Third point"],
        })
        assert "First point" in html
        assert "Second point" in html
        assert "Third point" in html

    def test_missing_styles_dir_returns_empty(self, tmp_path: Path):
        """When styles dir doesn't exist, CSS strings are empty but render succeeds."""
        engine = self._make_engine(styles_dir=tmp_path / "nonexistent")
        html = engine.render("single_image/insight", {"headline": "Test"})
        assert "Test" in html
        assert "--brand-color-primary" in html  # brand CSS still present
