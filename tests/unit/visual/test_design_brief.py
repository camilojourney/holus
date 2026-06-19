"""Tests for deterministic visual design brief selection."""

from __future__ import annotations

from holus.visual.design_brief import build_deterministic_visual_design_brief


def test_claim_chart_design_brief_sets_chart_specific_parameters() -> None:
    brief = build_deterministic_visual_design_brief(
        template_kind="claim_chart",
        route_mode="chart",
        text="Document carousels get 8.7% while image posts get 2.4%.",
    )

    assert brief.composition_pattern == "metric_hero_with_supporting_chart"
    assert brief.chart_family == "comparison"
    assert brief.chart_glyph == "rounded_bar_comparison"
    assert brief.bar_style == "winner_bar_accent_muted_context"
    assert "title states the conclusion" in " ".join(brief.compliance_checks)
    assert "tiny dashboard widgets" in brief.forbidden_elements


def test_operating_map_design_brief_sets_step_card_parameters() -> None:
    brief = build_deterministic_visual_design_brief(
        template_kind="operating_map",
        route_mode="workflow",
        text="Capture, refine, render, judge, queue.",
    )

    assert brief.html_layout == "step_card_grid"
    assert brief.mark_style == "numbered_step_cards"
    assert brief.label_policy == "imperative_verb_first_labels_max_three_words"
    assert "viewer can name the sequence" in " ".join(brief.compliance_checks)


def test_decision_surface_design_brief_sets_product_surface_parameters() -> None:
    brief = build_deterministic_visual_design_brief(
        template_kind="decision_surface",
        route_mode="product_scene",
        text="The workbench is a decision surface.",
    )

    assert brief.composition_pattern == "product_decision_surface"
    assert brief.html_layout == "before_after_decision_table"
    assert brief.surface_treatment == "large_table_card"
    assert "state change is visible" in " ".join(brief.compliance_checks)
