"""Visual proximity routing for refined social content.

The router decides the kind of image before any provider is called. This keeps
AI image generation from jumping straight from text into a vague metaphor.
"""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class VisualProximityMode(StrEnum):
    """How literally the visual should represent the refined idea."""

    WORKFLOW = "workflow"
    CHART = "chart"
    PERSON_STORY = "person_story"
    OBJECT_METAPHOR = "object_metaphor"
    PRODUCT_SCENE = "product_scene"
    TYPOGRAPHY_CARD = "typography_card"


class VisualConceptRoute(BaseModel):
    """Provider-facing decision about what kind of visual to create."""

    mode: VisualProximityMode
    proximity_score: int = Field(ge=1, le=5)
    viewer_takeaway: str
    scene: str
    subject: str
    composition: str
    use_person: bool = False
    use_chart: bool = False
    use_workflow: bool = False
    visual_do: list[str] = Field(default_factory=list)
    visual_dont: list[str] = Field(default_factory=list)
    rationale: str

    def prompt_contract(self) -> str:
        """Return a compact prompt contract for image providers."""
        yes = "; ".join(self.visual_do)
        no = "; ".join(self.visual_dont)
        return (
            f"Visual route: {self.mode.value}\n"
            f"Proximity score: {self.proximity_score}/5\n"
            f"Viewer takeaway: {self.viewer_takeaway}\n"
            f"Scene: {self.scene}\n"
            f"Subject: {self.subject}\n"
            f"Composition: {self.composition}\n"
            f"Use person: {self.use_person}\n"
            f"Use chart: {self.use_chart}\n"
            f"Use workflow: {self.use_workflow}\n"
            f"Do: {yes}\n"
            f"Do not: {no}\n"
            f"Routing rationale: {self.rationale}"
        )


def choose_visual_concept_route(source: Any) -> VisualConceptRoute:
    """Choose a visual mode from a refined source or queue-like object."""
    text = _source_text(source)
    lowered = text.lower()
    digest = hashlib.sha256(text.encode()).hexdigest()

    if _has_chart_signal(lowered):
        return VisualConceptRoute(
            mode=VisualProximityMode.CHART,
            proximity_score=5,
            viewer_takeaway=_takeaway(source, "The measurable comparison is the point."),
            scene="clean editorial chart or decision matrix",
            subject="one highlighted metric, comparison, or ranking from the refined argument",
            composition="large title, one simple chart, one highlighted bar or quadrant",
            use_chart=True,
            visual_do=[
                "make the data relationship visible immediately",
                "use one chart type only",
                "highlight the conclusion",
            ],
            visual_dont=_default_donts(),
            rationale="Numbers or explicit comparisons should stay close to the evidence.",
        )

    if _has_founder_artifact_signal(lowered):
        return _person_story_route(source)

    if _has_workflow_signal(lowered):
        return VisualConceptRoute(
            mode=VisualProximityMode.WORKFLOW,
            proximity_score=5,
            viewer_takeaway=_takeaway(source, "The workflow is job design, not one magic model."),
            scene="clear operating flow with distinct stations or roles",
            subject="planning, execution, skills, review, fallback, and daily work as separate jobs",
            composition="left-to-right or top-to-bottom flow with five labeled stages; one small model component inside the system",
            use_workflow=True,
            visual_do=[
                "show role separation",
                "make the workflow readable without the caption",
                "make the model only one part of the system",
            ],
            visual_dont=[
                *_default_donts(),
                "do not show abstract cables or unlabeled blank modules as the main idea",
            ],
            rationale="The refined content explains a system of roles, so the closest useful visual is a workflow.",
        )

    if _has_product_signal(lowered):
        return VisualConceptRoute(
            mode=VisualProximityMode.PRODUCT_SCENE,
            proximity_score=4,
            viewer_takeaway=_takeaway(source, "The product behavior should be visible."),
            scene="product interface or workspace showing the before-and-after state",
            subject="a real-looking product surface, review queue, or content planning board",
            composition="screen or board as hero, one visible state change, restrained editorial lighting",
            visual_do=[
                "show the product job",
                "make the before/after or state change obvious",
                "keep interface details plausible but not fake-text heavy",
            ],
            visual_dont=_default_donts(),
            rationale="Product, screen, queue, or interface language needs a concrete usage scene.",
        )

    if _has_typography_signal(lowered):
        return _typography_route(source)

    if _has_object_metaphor_signal(lowered):
        return _object_metaphor_route(source)

    if _has_person_signal(lowered):
        return _person_story_route(source)

    if int(digest[:2], 16) % 2 == 0:
        return _object_metaphor_route(source)

    return _typography_route(source)


def _object_metaphor_route(source: Any) -> VisualConceptRoute:
    return VisualConceptRoute(
        mode=VisualProximityMode.OBJECT_METAPHOR,
        proximity_score=2,
        viewer_takeaway=_takeaway(source, "One physical metaphor should make the idea memorable."),
        scene="single concrete editorial object metaphor",
        subject="one recognizable object directly mapped to the thesis",
        composition="one hero object, simple background, strong focal point, no clutter",
        visual_do=[
            "use one metaphor only",
            "make the metaphor explainable in one sentence",
            "keep it grounded and physical",
        ],
        visual_dont=[
            *_default_donts(),
            "do not create a generic premium desk object collection",
        ],
        rationale="A concrete object-metaphor signal was detected before any generic human or workflow framing.",
    )


def _person_story_route(source: Any) -> VisualConceptRoute:
    return VisualConceptRoute(
        mode=VisualProximityMode.PERSON_STORY,
        proximity_score=3,
        viewer_takeaway=_takeaway(source, "The viewer should recognize the human situation."),
        scene="editorial workplace moment with one person facing the problem",
        subject="a founder, operator, reviewer, or customer making the decision visible",
        composition="person in foreground, decision artifact visible, environment grounded and realistic",
        use_person=True,
        visual_do=[
            "show a believable human moment",
            "include one concrete artifact tied to the idea",
            "keep the scene editorial, not stock-photo corporate",
        ],
        visual_dont=_default_donts(),
        rationale="Human-role or lived-experience language should route to a story before a diagram.",
    )


def _typography_route(source: Any) -> VisualConceptRoute:
    return VisualConceptRoute(
        mode=VisualProximityMode.TYPOGRAPHY_CARD,
        proximity_score=4,
        viewer_takeaway=_takeaway(source, "The thesis itself is the asset."),
        scene="designed editorial thesis card",
        subject="one strong sentence from the refined content",
        composition="large thesis, short proof line, high contrast, no decorative image",
        visual_do=[
            "make the thesis readable instantly",
            "use restrained typography and strong hierarchy",
            "keep visual noise low",
        ],
        visual_dont=_default_donts(),
        rationale="The idea is abstract and benefits from direct editorial clarity.",
    )


def _source_text(source: Any) -> str:
    if isinstance(source, dict):
        thought_essence = source.get("thought_essence")
        visual_prompt = (
            thought_essence.get("visual_prompt") if isinstance(thought_essence, dict) else ""
        )
        return (
            " ".join(
                str(source.get(key, "") or "")
                for key in ("refined_text", "text", "topic", "headline", "intended_takeaway")
            )
            + f" {visual_prompt or ''}"
        )
    thought_essence = getattr(source, "thought_essence", None)
    visual_prompt = (
        thought_essence.get("visual_prompt") if isinstance(thought_essence, dict) else ""
    )
    return (
        " ".join(
            str(getattr(source, key, "") or "")
            for key in ("refined_text", "topic", "headline", "intended_takeaway")
        )
        + f" {visual_prompt or ''}"
    )


def _takeaway(source: Any, fallback: str) -> str:
    if isinstance(source, dict):
        value = source.get("intended_takeaway") or source.get("topic") or source.get("headline")
    else:
        value = (
            getattr(source, "intended_takeaway", None)
            or getattr(source, "topic", None)
            or getattr(source, "headline", None)
        )
    return str(value or fallback)


def _has_chart_signal(lowered: str) -> bool:
    return bool(
        "%" in lowered
        or re.search(r"\b(metric|data|chart|rank|compare|versus|vs|percent)\b", lowered)
        or any(
            signal in lowered
            for signal in ("spreadsheet", "retention", "saves", "impressions", "replies")
        )
    )


def _has_workflow_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(workflow|pipeline|process|playbook|templates|content systems|brand formats|harness|handoff|sequence|loop|cycle|orchestration|step|stages|planning|execution|capture|extract|refine|render|judge|fallback|grid|hierarchy|padding|stroke)\b",
            lowered,
        )
    )


def _has_person_signal(lowered: str) -> bool:
    lexical_signal = any(
        signal in lowered
        for signal in (
            "i learned",
            "founder",
            "customer",
            "client",
            "team",
            "operator",
            "person",
            "reviewer",
            "watched",
            "pointed",
            "points",
            "marks",
            "circles",
            "creator",
        )
    )
    return lexical_signal or bool(re.search(r"\b(she|he)\b", lowered))


def _has_founder_artifact_signal(lowered: str) -> bool:
    return bool(
        re.search(r"\b(founder|operator|creator)\b", lowered)
        and re.search(r"\b(points|pointed|marks|marked|sentence|line|draft|artifact)\b", lowered)
    )


def _has_product_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(product|demo|interface|dashboard|app|queue|studio|draft|approve|reject|workbench|surface)\b",
            lowered,
        )
        or any(signal in lowered for signal in ("fit signal", "review surface", "decision surface"))
    )


def _has_typography_signal(lowered: str) -> bool:
    return any(
        signal in lowered
        for signal in (
            "needs the caption",
            "need the caption",
            "without the caption",
            "image should carry",
            "visual should carry",
            "thesis before the caption",
            "it is decoration",
            "not done",
        )
    )


def _has_object_metaphor_signal(lowered: str) -> bool:
    return any(
        signal in lowered
        for signal in (
            "like a",
            "like an",
            "pile",
            "sticky",
            "bridge",
            "gap",
            "compass",
            "blueprint",
            "map",
            "legend",
            "lens",
            "factory",
            "train",
            "car",
            "cargo",
            "station",
            "calendar",
        )
    )


def _default_donts() -> list[str]:
    return [
        "generic AI wallpaper",
        "glowing brain",
        "robot mascot",
        "abstract network background",
        "pseudo-text",
        "random premium objects with unclear meaning",
    ]
