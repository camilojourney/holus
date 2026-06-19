"""Provider and design strategy selection for LinkedIn visual assets."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from holus.visual.content_job import ContentJobPlan, plan_content_job
from holus.visual.design_brief import (
    DeterministicVisualDesignBrief,
    build_deterministic_visual_design_brief,
)
from holus.visual.dispatcher import VisualProvider
from holus.visual.proximity_router import VisualConceptRoute, VisualProximityMode


class VisualRenderingPath(StrEnum):
    """How the visual should be produced."""

    NO_VISUAL = "no_visual"
    DETERMINISTIC_TEMPLATE = "deterministic_template"
    AI_IMAGE = "ai_image"
    HYBRID = "hybrid"


class VisualTemplateKind(StrEnum):
    """Template family or AI image family selected for the visual."""

    NO_VISUAL = "no_visual"
    NEWS_BATTLECARD = "news_battlecard"
    CLAIM_CHART = "claim_chart"
    OPERATING_MAP = "operating_map"
    DECISION_SURFACE = "decision_surface"
    THESIS_POSTER = "thesis_poster"
    COMPARISON_TABLE = "comparison_table"
    FRAMEWORK_GRID = "framework_grid"
    ARTIFACT_STORY = "artifact_story"
    SINGLE_METAPHOR = "single_metaphor"


class VisualPaletteName(StrEnum):
    """Named palette systems for deterministic visual variation."""

    SIGNAL_DARK = "signal_dark"
    EDITORIAL_LIGHT = "editorial_light"
    TEAL_AMBER = "teal_amber"
    RED_GREEN_COMPARE = "red_green_compare"
    BLUE_LIME_TECH = "blue_lime_tech"
    MONO_ACCENT = "mono_accent"
    NOTEBOOK_WARM = "notebook_warm"


class VisualDesignSystem(BaseModel):
    """Concrete design decisions passed to deterministic renderers or prompts."""

    palette: VisualPaletteName
    background: str
    foreground: str
    accent: str
    secondary_accent: str
    positive: str
    negative: str
    typography: str
    layout_density: str
    texture: str
    icon_style: str
    chart_style: str
    guardrails: list[str] = Field(default_factory=list)

    def prompt_directive(self) -> str:
        """Return provider-facing design instructions."""
        return (
            f"Design system: {self.palette.value}. "
            f"Background {self.background}, foreground {self.foreground}, accent {self.accent}, "
            f"secondary accent {self.secondary_accent}. Typography: {self.typography}. "
            f"Density: {self.layout_density}. Texture: {self.texture}. "
            f"Icons: {self.icon_style}. Charts: {self.chart_style}. "
            f"Guardrails: {'; '.join(self.guardrails)}"
        )


class VisualGenerationStrategy(BaseModel):
    """Final recommendation for how to produce one LinkedIn visual."""

    rendering_path: VisualRenderingPath
    provider: VisualProvider
    template_kind: VisualTemplateKind
    design_system: VisualDesignSystem
    content_job: ContentJobPlan
    deterministic_score: float = Field(ge=0.0, le=1.0)
    ai_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    required_inputs: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    design_brief: DeterministicVisualDesignBrief | None = None

    def log_summary(self) -> dict[str, Any]:
        """Return compact strategy metadata for logs."""
        return {
            "rendering_path": self.rendering_path.value,
            "provider": self.provider.value,
            "template_kind": self.template_kind.value,
            "content_job": self.content_job.job_type.value,
            "needs_visual": self.content_job.needs_visual,
            "palette": self.design_system.palette.value,
            "deterministic_score": self.deterministic_score,
            "ai_score": self.ai_score,
            "rationale": self.rationale,
            "design_brief": (
                self.design_brief.model_dump(mode="json") if self.design_brief else None
            ),
        }


def choose_visual_generation_strategy(
    source: Any,
    route: VisualConceptRoute,
) -> VisualGenerationStrategy:
    """Choose deterministic vs AI generation plus design system."""
    text = _source_text(source)
    lowered = text.lower()
    content_job = plan_content_job(source)
    if not content_job.needs_visual:
        pattern = VisualTemplateKind.NO_VISUAL
        rendering_path = VisualRenderingPath.NO_VISUAL
    else:
        pattern = _template_kind(lowered, route.mode)
        rendering_path = _rendering_path(pattern, route.mode)
        if rendering_path == VisualRenderingPath.AI_IMAGE and not content_job.ai_image_allowed:
            pattern = _deterministic_fallback_template(route.mode)
            rendering_path = VisualRenderingPath.DETERMINISTIC_TEMPLATE
    provider = (
        VisualProvider.CODEX_CLI_IMAGE
        if rendering_path in {VisualRenderingPath.AI_IMAGE, VisualRenderingPath.HYBRID}
        else VisualProvider.HTML_RENDERER
    )
    deterministic_score, ai_score = _scores(rendering_path, route.mode)
    design_system = _design_system(text, pattern, route.mode)
    design_brief = (
        build_deterministic_visual_design_brief(
            template_kind=pattern.value,
            route_mode=route.mode.value,
            text=text,
        )
        if rendering_path == VisualRenderingPath.DETERMINISTIC_TEMPLATE
        else None
    )
    return VisualGenerationStrategy(
        rendering_path=rendering_path,
        provider=provider,
        template_kind=pattern,
        design_system=design_system,
        content_job=content_job,
        deterministic_score=deterministic_score,
        ai_score=ai_score,
        rationale=_rationale(rendering_path, pattern, route.mode),
        required_inputs=_required_inputs(pattern),
        failure_modes=_failure_modes(rendering_path, pattern),
        design_brief=design_brief,
    )


def _template_kind(lowered: str, mode: VisualProximityMode) -> VisualTemplateKind:
    if _has_news_battlecard_signal(lowered):
        return VisualTemplateKind.NEWS_BATTLECARD
    if mode == VisualProximityMode.CHART:
        return VisualTemplateKind.CLAIM_CHART
    if mode == VisualProximityMode.WORKFLOW:
        if any(signal in lowered for signal in ("framework", "layers", "matrix")):
            return VisualTemplateKind.FRAMEWORK_GRID
        return VisualTemplateKind.OPERATING_MAP
    if mode == VisualProximityMode.PRODUCT_SCENE:
        return VisualTemplateKind.DECISION_SURFACE
    if mode == VisualProximityMode.TYPOGRAPHY_CARD:
        return VisualTemplateKind.THESIS_POSTER
    if mode == VisualProximityMode.PERSON_STORY:
        return VisualTemplateKind.ARTIFACT_STORY
    if mode == VisualProximityMode.OBJECT_METAPHOR:
        return VisualTemplateKind.SINGLE_METAPHOR
    return VisualTemplateKind.THESIS_POSTER


def _rendering_path(
    template_kind: VisualTemplateKind,
    mode: VisualProximityMode,
) -> VisualRenderingPath:
    if template_kind in {
        VisualTemplateKind.NEWS_BATTLECARD,
        VisualTemplateKind.CLAIM_CHART,
        VisualTemplateKind.OPERATING_MAP,
        VisualTemplateKind.DECISION_SURFACE,
        VisualTemplateKind.THESIS_POSTER,
        VisualTemplateKind.COMPARISON_TABLE,
        VisualTemplateKind.FRAMEWORK_GRID,
    }:
        return VisualRenderingPath.DETERMINISTIC_TEMPLATE
    if mode == VisualProximityMode.PERSON_STORY:
        return VisualRenderingPath.HYBRID
    return VisualRenderingPath.AI_IMAGE


def _deterministic_fallback_template(mode: VisualProximityMode) -> VisualTemplateKind:
    if mode == VisualProximityMode.CHART:
        return VisualTemplateKind.CLAIM_CHART
    if mode == VisualProximityMode.WORKFLOW:
        return VisualTemplateKind.OPERATING_MAP
    if mode == VisualProximityMode.PRODUCT_SCENE:
        return VisualTemplateKind.DECISION_SURFACE
    return VisualTemplateKind.THESIS_POSTER


def _scores(
    rendering_path: VisualRenderingPath,
    mode: VisualProximityMode,
) -> tuple[float, float]:
    if rendering_path == VisualRenderingPath.NO_VISUAL:
        return 0.0, 0.0
    if rendering_path == VisualRenderingPath.DETERMINISTIC_TEMPLATE:
        return 0.9, 0.25
    if rendering_path == VisualRenderingPath.HYBRID:
        return 0.55, 0.7
    if mode == VisualProximityMode.OBJECT_METAPHOR:
        return 0.35, 0.85
    return 0.4, 0.75


def _design_system(
    text: str,
    template_kind: VisualTemplateKind,
    mode: VisualProximityMode,
) -> VisualDesignSystem:
    palette = _choose_palette(text, template_kind, mode)
    variants = _palette_variants()[palette]
    return VisualDesignSystem(
        palette=palette,
        background=variants["background"],
        foreground=variants["foreground"],
        accent=variants["accent"],
        secondary_accent=variants["secondary_accent"],
        positive=variants["positive"],
        negative=variants["negative"],
        typography=variants["typography"],
        layout_density=_layout_density(template_kind),
        texture=variants["texture"],
        icon_style=variants["icon_style"],
        chart_style=variants["chart_style"],
        guardrails=[
            "mobile-first 1080x1350 or 1080x1080 safe hierarchy",
            "one focal claim before details",
            "consistent padding and stroke widths",
            "no tiny pseudo text",
        ],
    )


def _choose_palette(
    text: str,
    template_kind: VisualTemplateKind,
    mode: VisualProximityMode,
) -> VisualPaletteName:
    lowered = text.lower()
    if template_kind == VisualTemplateKind.NO_VISUAL:
        return VisualPaletteName.MONO_ACCENT
    if template_kind == VisualTemplateKind.NEWS_BATTLECARD:
        return VisualPaletteName.RED_GREEN_COMPARE
    if any(signal in lowered for signal in ("risk", "warning", "lost", "fail", "less")):
        return VisualPaletteName.SIGNAL_DARK
    if any(signal in lowered for signal in ("growth", "win", "faster", "better")):
        return VisualPaletteName.BLUE_LIME_TECH
    if mode == VisualProximityMode.PERSON_STORY:
        return VisualPaletteName.NOTEBOOK_WARM
    if mode == VisualProximityMode.TYPOGRAPHY_CARD:
        return VisualPaletteName.MONO_ACCENT
    digest = int(hashlib.sha256(text.encode()).hexdigest()[:2], 16)
    return [
        VisualPaletteName.EDITORIAL_LIGHT,
        VisualPaletteName.TEAL_AMBER,
        VisualPaletteName.BLUE_LIME_TECH,
    ][digest % 3]


def _palette_variants() -> dict[VisualPaletteName, dict[str, str]]:
    return {
        VisualPaletteName.SIGNAL_DARK: {
            "background": "#111216",
            "foreground": "#F4F1EA",
            "accent": "#E23D3D",
            "secondary_accent": "#28B463",
            "positive": "#56C271",
            "negative": "#E23D3D",
            "typography": "condensed bold headline with neutral sans support",
            "texture": "subtle dark grain",
            "icon_style": "thin-line utility icons",
            "chart_style": "high contrast table or bar comparison",
        },
        VisualPaletteName.EDITORIAL_LIGHT: {
            "background": "#F6F1E8",
            "foreground": "#1E2428",
            "accent": "#0C7C84",
            "secondary_accent": "#D99A2B",
            "positive": "#16875A",
            "negative": "#C7483A",
            "typography": "editorial serif headline with clean sans labels",
            "texture": "paper texture",
            "icon_style": "flat editorial symbols",
            "chart_style": "minimal axis with one highlighted mark",
        },
        VisualPaletteName.TEAL_AMBER: {
            "background": "#F8F6EF",
            "foreground": "#172326",
            "accent": "#007A7A",
            "secondary_accent": "#E6A23C",
            "positive": "#228B62",
            "negative": "#B94A48",
            "typography": "bold grotesk headline with compact labels",
            "texture": "warm paper",
            "icon_style": "rounded line icons",
            "chart_style": "teal primary data with amber callout",
        },
        VisualPaletteName.RED_GREEN_COMPARE: {
            "background": "#0D0F12",
            "foreground": "#F5F5F2",
            "accent": "#E52E2E",
            "secondary_accent": "#68B545",
            "positive": "#68B545",
            "negative": "#E52E2E",
            "typography": "compressed uppercase headline with tabular numerals",
            "texture": "dark vignette with clean grid",
            "icon_style": "sharp comparison icons",
            "chart_style": "battlecard table with red/green sides",
        },
        VisualPaletteName.BLUE_LIME_TECH: {
            "background": "#092A35",
            "foreground": "#F4FAF8",
            "accent": "#B9F45E",
            "secondary_accent": "#3BA7C9",
            "positive": "#B9F45E",
            "negative": "#F46D5E",
            "typography": "wide tech sans headline with mono labels",
            "texture": "flat technical matte",
            "icon_style": "geometric system icons",
            "chart_style": "technical grid with bright active series",
        },
        VisualPaletteName.MONO_ACCENT: {
            "background": "#FAF7EF",
            "foreground": "#111111",
            "accent": "#006D77",
            "secondary_accent": "#D9902F",
            "positive": "#187A55",
            "negative": "#B73E3E",
            "typography": "large editorial serif or heavy grotesk thesis",
            "texture": "clean paper",
            "icon_style": "none or one accent rule",
            "chart_style": "not applicable unless support line needs a mark",
        },
        VisualPaletteName.NOTEBOOK_WARM: {
            "background": "#F3EBDD",
            "foreground": "#202124",
            "accent": "#C66A2E",
            "secondary_accent": "#406E8E",
            "positive": "#2E7D5B",
            "negative": "#A9473D",
            "typography": "human editorial sans with handwritten annotation accent",
            "texture": "notebook paper",
            "icon_style": "hand-marked annotations",
            "chart_style": "marked artifact or simple callout",
        },
    }


def _layout_density(template_kind: VisualTemplateKind) -> str:
    if template_kind == VisualTemplateKind.NO_VISUAL:
        return "none: text-only content job"
    if template_kind == VisualTemplateKind.NEWS_BATTLECARD:
        return "dense but gridded: headline, comparison, evidence grid, verdict"
    if template_kind in {VisualTemplateKind.CLAIM_CHART, VisualTemplateKind.DECISION_SURFACE}:
        return "medium: one evidence block plus verdict"
    if template_kind == VisualTemplateKind.THESIS_POSTER:
        return "sparse: thesis plus one support line"
    return "sparse-to-medium with one focal object or sequence"


def _required_inputs(template_kind: VisualTemplateKind) -> list[str]:
    if template_kind == VisualTemplateKind.NO_VISUAL:
        return ["approved text post"]
    if template_kind == VisualTemplateKind.NEWS_BATTLECARD:
        return ["claim", "two subjects", "numeric delta", "3-5 sourced evidence rows", "verdict"]
    if template_kind == VisualTemplateKind.CLAIM_CHART:
        return ["claim", "one metric relationship", "highlighted value", "verdict"]
    if template_kind == VisualTemplateKind.DECISION_SURFACE:
        return ["selected item", "reason/evidence", "decision state"]
    if template_kind == VisualTemplateKind.OPERATING_MAP:
        return ["input", "4-6 stages", "bottleneck", "output"]
    if template_kind == VisualTemplateKind.THESIS_POSTER:
        return ["exact thesis", "support line"]
    if template_kind == VisualTemplateKind.ARTIFACT_STORY:
        return ["decision-maker", "artifact", "gesture/action"]
    return ["metaphor object", "tension", "verdict"]


def _failure_modes(
    rendering_path: VisualRenderingPath,
    template_kind: VisualTemplateKind,
) -> list[str]:
    if rendering_path == VisualRenderingPath.NO_VISUAL:
        return ["adding a visual anyway", "weak writing", "unclear text-only thesis"]
    common = ["unclear claim", "weak mobile hierarchy", "caption-dependent visual"]
    if rendering_path == VisualRenderingPath.DETERMINISTIC_TEMPLATE:
        return [*common, "over-dense template", "missing evidence data"]
    if template_kind == VisualTemplateKind.ARTIFACT_STORY:
        return [*common, "stock-photo person", "artifact not visible"]
    return [*common, "generic AI metaphor", "decorative scene without proof"]


def _rationale(
    rendering_path: VisualRenderingPath,
    template_kind: VisualTemplateKind,
    mode: VisualProximityMode,
) -> str:
    if rendering_path == VisualRenderingPath.NO_VISUAL:
        return "The content job is better served as text; no visual should be produced by default."
    if rendering_path == VisualRenderingPath.DETERMINISTIC_TEMPLATE:
        return (
            f"{template_kind.value} needs exact layout, text, proof, and mobile hierarchy; "
            "deterministic rendering is safer than AI image generation."
        )
    if rendering_path == VisualRenderingPath.HYBRID:
        return (
            f"{mode.value} needs a human/artifact moment, but should stay constrained by a "
            "deterministic layout and design system."
        )
    return (
        f"{mode.value} benefits from generative imagery because the core value is metaphor or mood."
    )


def _has_news_battlecard_signal(lowered: str) -> bool:
    return bool(
        re.search(r"\b(vs|versus)\b", lowered)
        or "$" in lowered
        or any(signal in lowered for signal in (" less", " cheaper", "competitor"))
    )


def _source_text(source: Any) -> str:
    if isinstance(source, dict):
        return " ".join(
            str(source.get(key, "") or "")
            for key in ("refined_text", "text", "topic", "headline", "intended_takeaway")
        )
    return " ".join(
        str(getattr(source, key, "") or "")
        for key in ("refined_text", "topic", "headline", "intended_takeaway")
    )
