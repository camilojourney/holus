"""Deterministic visual design contracts for renderer selection.

This module is intentionally provider-neutral. It does not draw charts or
slides; it converts a routed visual into explicit design parameters that the
HTML/SVG renderers must obey.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class DeterministicVisualDesignBrief(BaseModel):
    """Renderer-facing design contract for one deterministic visual."""

    template_kind: str
    composition_pattern: str
    html_layout: str
    palette_role: str
    background_style: str
    typography_scale: str
    surface_treatment: str
    density: str
    mark_style: str
    chart_family: str | None = None
    chart_glyph: str | None = None
    bar_style: str | None = None
    axis_policy: str | None = None
    label_policy: str
    compliance_checks: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)
    inspiration_refs: list[str] = Field(default_factory=list)
    variation_seed: str

    def prompt_contract(self) -> str:
        """Return a compact contract for AI or HTML designers."""
        chart_bits = [
            f"Chart family: {self.chart_family}" if self.chart_family else "",
            f"Chart glyph: {self.chart_glyph}" if self.chart_glyph else "",
            f"Bar style: {self.bar_style}" if self.bar_style else "",
            f"Axis policy: {self.axis_policy}" if self.axis_policy else "",
        ]
        chart_block = "\n".join(bit for bit in chart_bits if bit)
        return (
            "Deterministic visual design brief:\n"
            f"Template kind: {self.template_kind}\n"
            f"Composition: {self.composition_pattern}\n"
            f"HTML layout: {self.html_layout}\n"
            f"Palette role: {self.palette_role}\n"
            f"Background: {self.background_style}\n"
            f"Typography: {self.typography_scale}\n"
            f"Surface: {self.surface_treatment}\n"
            f"Density: {self.density}\n"
            f"Mark style: {self.mark_style}\n"
            f"Label policy: {self.label_policy}\n"
            f"{chart_block}\n"
            f"Compliance: {'; '.join(self.compliance_checks)}\n"
            f"Forbidden: {'; '.join(self.forbidden_elements)}\n"
            f"Inspiration refs: {'; '.join(self.inspiration_refs)}"
        ).strip()

    def render_variables(self) -> dict[str, str | list[str]]:
        """Return flattened template variables accepted by RenderSpec."""
        return {
            "composition_pattern": self.composition_pattern,
            "html_layout": self.html_layout,
            "palette_role": self.palette_role,
            "background_style": self.background_style,
            "typography_scale": self.typography_scale,
            "surface_treatment": self.surface_treatment,
            "density": self.density,
            "mark_style": self.mark_style,
            "chart_family": self.chart_family or "",
            "chart_glyph": self.chart_glyph or "",
            "bar_style": self.bar_style or "",
            "axis_policy": self.axis_policy or "",
            "label_policy": self.label_policy,
            "design_compliance_checks": self.compliance_checks,
            "design_inspiration_refs": self.inspiration_refs,
            "variation_seed": self.variation_seed,
        }


def build_deterministic_visual_design_brief(
    *,
    template_kind: str,
    route_mode: str,
    text: str,
) -> DeterministicVisualDesignBrief:
    """Choose deterministic renderer parameters from route + source text."""
    lowered = text.lower()
    seed = hashlib.sha256(f"{template_kind}|{route_mode}|{text}".encode()).hexdigest()[:12]

    if template_kind == "claim_chart":
        return DeterministicVisualDesignBrief(
            template_kind=template_kind,
            composition_pattern="metric_hero_with_supporting_chart",
            html_layout="editorial_metric_card",
            palette_role="single_accent_for_winner",
            background_style="light_editorial_gradient",
            typography_scale="large_conclusion_then_chart",
            surface_treatment="raised_white_data_card",
            density="medium",
            mark_style="large_rounded_bars",
            chart_family="comparison",
            chart_glyph=_chart_glyph(lowered),
            bar_style="winner_bar_accent_muted_context",
            axis_policy="baseline_only_no_grid_clutter",
            label_policy="wrap_labels_under_16_chars_and_show_values_above_marks",
            compliance_checks=[
                "title states the conclusion, not the topic",
                "one highlighted winner or anomaly",
                "labels remain readable at 360px preview width",
                "no decorative data clutter",
            ],
            forbidden_elements=[
                "tiny dashboard widgets",
                "multiple competing chart types",
                "unlabeled bars",
                "gradient-only backgrounds without data hierarchy",
            ],
            inspiration_refs=[
                "Carbon purpose-first chart taxonomy",
                "IBM comparison chart guidance",
                "OpenAI minimal card discipline",
            ],
            variation_seed=seed,
        )

    if template_kind in {"operating_map", "framework_grid"}:
        return DeterministicVisualDesignBrief(
            template_kind=template_kind,
            composition_pattern="numbered_operating_board",
            html_layout="step_card_grid",
            palette_role="cool_blue_system_accent",
            background_style="light_product_surface",
            typography_scale="large_process_claim_with_card_labels",
            surface_treatment="product_board_with_numbered_cards",
            density="structured",
            mark_style="numbered_step_cards",
            chart_family="process",
            chart_glyph="step_grid",
            bar_style=None,
            axis_policy=None,
            label_policy="imperative_verb_first_labels_max_three_words",
            compliance_checks=[
                "viewer can name the sequence without the caption",
                "each step is visually separate",
                "model or AI is one component, not magic wallpaper",
                "labels are verbs, not generic nouns",
            ],
            forbidden_elements=[
                "abstract network background",
                "unlabeled boxes",
                "five tiny boxes in a huge empty card",
                "decorative arrows that do not encode sequence",
            ],
            inspiration_refs=[
                "Linear quiet product-surface discipline",
                "reveal.js HTML-first slide composition",
                "Satori HTML/CSS-to-image layout model",
            ],
            variation_seed=seed,
        )

    if template_kind in {"decision_surface", "news_battlecard", "comparison_table"}:
        return DeterministicVisualDesignBrief(
            template_kind=template_kind,
            composition_pattern="product_decision_surface",
            html_layout="before_after_decision_table",
            palette_role="warm_decision_accent",
            background_style="light_warm_product_surface",
            typography_scale="decision_claim_then_table",
            surface_treatment="large_table_card",
            density="compact_but_legible",
            mark_style="large_rows_with_clear_verdict",
            chart_family="comparison",
            chart_glyph="before_after_table",
            bar_style=None,
            axis_policy=None,
            label_policy="dimension_centered_short_before_after_values",
            compliance_checks=[
                "state change is visible in under three seconds",
                "before and after labels are explicit",
                "winner/verdict uses both position and color",
                "no fake product microcopy",
            ],
            forbidden_elements=[
                "tiny comparison table",
                "ambiguous before/after state",
                "random dashboard widgets",
                "fake UI chrome that implies real product data",
            ],
            inspiration_refs=[
                "Stripe clean card-based dashboard hierarchy",
                "Material contextual data visualization shapes",
                "OpenAI simple white-card restraint",
            ],
            variation_seed=seed,
        )

    if template_kind == "thesis_poster":
        return DeterministicVisualDesignBrief(
            template_kind=template_kind,
            composition_pattern="editorial_thesis_poster",
            html_layout="large_type_with_support_line",
            palette_role="mono_accent",
            background_style="quiet_editorial_gradient",
            typography_scale="hero_sentence_first",
            surface_treatment="unframed_editorial_canvas",
            density="low",
            mark_style="typographic_emphasis",
            label_policy="one_sentence_no_tiny_support_copy",
            compliance_checks=[
                "one thesis dominates the canvas",
                "support text does not repeat the headline",
                "readable at mobile feed size",
            ],
            forbidden_elements=["generic quote card", "tiny footer-heavy layout"],
            inspiration_refs=["OpenAI typography scale", "Anthropic calm brand restraint"],
            variation_seed=seed,
        )

    return DeterministicVisualDesignBrief(
        template_kind=template_kind,
        composition_pattern="editorial_visual_default",
        html_layout="single_focus_card",
        palette_role="single_accent",
        background_style="light_editorial_surface",
        typography_scale="one_claim_one_mark",
        surface_treatment="simple_card",
        density="medium",
        mark_style="single_visual_mark",
        label_policy="short_labels_only",
        compliance_checks=["one clear focal point", "no tiny pseudo text"],
        forbidden_elements=["generic AI wallpaper", "decorative clutter"],
        inspiration_refs=["Material data visualization guidance"],
        variation_seed=seed,
    )


def _chart_glyph(lowered: str) -> str:
    if any(signal in lowered for signal in ("trend", "over time", "month", "week")):
        return "line_or_slope_when_supported"
    if any(signal in lowered for signal in ("percent", "%", "versus", "vs", "compare")):
        return "rounded_bar_comparison"
    return "metric_bar"


def render_variables_from_payload(payload: Any) -> dict[str, str | list[str]]:
    """Parse a dumped brief payload and return render variables."""
    if not isinstance(payload, dict):
        return {}
    return DeterministicVisualDesignBrief.model_validate(payload).render_variables()
