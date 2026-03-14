from __future__ import annotations

from holus.visual.templates import TemplateEngine

engine = TemplateEngine()


def test_insight_template_renders_headline() -> None:
    html = engine.render("single_image/insight", {"headline": "Test"})
    assert "Test" in html


def test_insight_template_renders_stat() -> None:
    html = engine.render(
        "single_image/insight",
        {"headline": "X", "stat_value": "42x", "stat_label": "faster"},
    )
    assert "42x" in html
    assert "faster" in html


def test_hook_slide_renders_headline() -> None:
    html = engine.render(
        "carousel/hook_slide",
        {"headline": "My Hook", "slide_number": 1, "total_slides": 3},
    )
    assert "My Hook" in html
    assert "1" in html


def test_body_slide_renders_bullets() -> None:
    html = engine.render(
        "carousel/body_slide",
        {"title": "Speed", "bullets": ["Fast", "Reliable"], "slide_number": 2, "total_slides": 3},
    )
    assert "Fast" in html
    assert "Reliable" in html


def test_data_viz_template_renders_title() -> None:
    html = engine.render("single_image/data_viz", {"title": "Growth", "svg_content": "<svg></svg>"})
    assert "Growth" in html


def test_template_includes_brand_css() -> None:
    html = engine.render("single_image/insight", {"headline": "Brand"})
    assert "--brand-" in html
