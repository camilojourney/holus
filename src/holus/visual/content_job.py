"""Content job classification and visual necessity gating."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ContentJobType(StrEnum):
    """Strategic job a content item is trying to perform."""

    OPINION = "opinion"
    LESSON = "lesson"
    FRAMEWORK = "framework"
    WORKFLOW_EXPLANATION = "workflow_explanation"
    DATA_CLAIM = "data_claim"
    PRODUCT_UPDATE = "product_update"
    FOUNDER_STORY = "founder_story"
    METAPHOR = "metaphor"
    CASE_STUDY = "case_study"


class RecommendedContentFormat(StrEnum):
    """Primary artifact format recommended before provider selection."""

    TEXT_POST = "text_post"
    TEXT_WITH_DETERMINISTIC_VISUAL = "text_with_deterministic_visual"
    CAROUSEL_DOCUMENT = "carousel_document"
    AI_GENERATED_IMAGE = "ai_generated_image"
    VIDEO_REEL = "video_reel"


class VisualNeedReason(StrEnum):
    """Why a visual is or is not needed."""

    NO_VISUAL_NEEDED = "no_visual_needed"
    VISUAL_EXPLAINS_STRUCTURE = "visual_explains_structure"
    VISUAL_PROVES_DATA = "visual_proves_data"
    VISUAL_PACKAGES_FRAMEWORK = "visual_packages_framework"
    VISUAL_SHOWS_PRODUCT_STATE = "visual_shows_product_state"
    VISUAL_CARRIES_METAPHOR = "visual_carries_metaphor"
    VISUAL_SUPPORTS_STORY = "visual_supports_story"


class ContentJobPlan(BaseModel):
    """Planning decision used before any renderer or image provider runs."""

    job_type: ContentJobType
    needs_visual: bool
    reason: VisualNeedReason
    recommended_format: RecommendedContentFormat
    forbidden_formats: list[RecommendedContentFormat] = Field(default_factory=list)
    deterministic_allowed: bool
    ai_image_allowed: bool
    judge: str
    rationale: str

    def log_summary(self) -> dict[str, Any]:
        """Return compact metadata for logs and queue records."""
        return {
            "job_type": self.job_type.value,
            "needs_visual": self.needs_visual,
            "reason": self.reason.value,
            "recommended_format": self.recommended_format.value,
            "forbidden_formats": [item.value for item in self.forbidden_formats],
            "deterministic_allowed": self.deterministic_allowed,
            "ai_image_allowed": self.ai_image_allowed,
            "judge": self.judge,
            "rationale": self.rationale,
        }


def plan_content_job(source: Any) -> ContentJobPlan:
    """Classify content and decide whether visual production is justified."""
    text = _source_text(source)
    lowered = text.lower()

    if _looks_like_text_only_thesis(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.OPINION,
            needs_visual=False,
            reason=VisualNeedReason.NO_VISUAL_NEEDED,
            recommended_format=RecommendedContentFormat.TEXT_POST,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=False,
            ai_image_allowed=False,
            judge="written-content-judge",
            rationale="The idea is a compact thesis; adding a visual would likely dilute it.",
        )

    if _has_data_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.DATA_CLAIM,
            needs_visual=True,
            reason=VisualNeedReason.VISUAL_PROVES_DATA,
            recommended_format=RecommendedContentFormat.TEXT_WITH_DETERMINISTIC_VISUAL,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=True,
            ai_image_allowed=False,
            judge="visual-content-judge",
            rationale="Data-backed claims need exact values, labels, and proof hierarchy.",
        )

    if _has_workflow_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.WORKFLOW_EXPLANATION,
            needs_visual=True,
            reason=VisualNeedReason.VISUAL_EXPLAINS_STRUCTURE,
            recommended_format=RecommendedContentFormat.CAROUSEL_DOCUMENT,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=True,
            ai_image_allowed=False,
            judge="visual-content-judge",
            rationale="Workflows need readable steps and handoffs.",
        )

    if _has_framework_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.FRAMEWORK,
            needs_visual=True,
            reason=VisualNeedReason.VISUAL_PACKAGES_FRAMEWORK,
            recommended_format=RecommendedContentFormat.CAROUSEL_DOCUMENT,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=True,
            ai_image_allowed=False,
            judge="visual-content-judge",
            rationale="Frameworks work best as saveable document structure.",
        )

    if _has_product_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.PRODUCT_UPDATE,
            needs_visual=True,
            reason=VisualNeedReason.VISUAL_SHOWS_PRODUCT_STATE,
            recommended_format=RecommendedContentFormat.TEXT_WITH_DETERMINISTIC_VISUAL,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=True,
            ai_image_allowed=False,
            judge="visual-content-judge",
            rationale="Product updates need plausible state, UI, or before/after evidence.",
        )

    if _has_founder_story_signal(lowered):
        has_concrete_artifact = bool(
            re.search(
                r"\b(artifact|draft|line|sentence|screen|note|voice note|points at|marked|mark|document)\b",
                lowered,
            )
        )
        return ContentJobPlan(
            job_type=ContentJobType.FOUNDER_STORY,
            needs_visual=has_concrete_artifact,
            reason=(
                VisualNeedReason.VISUAL_SUPPORTS_STORY
                if has_concrete_artifact
                else VisualNeedReason.NO_VISUAL_NEEDED
            ),
            recommended_format=(
                RecommendedContentFormat.TEXT_WITH_DETERMINISTIC_VISUAL
                if has_concrete_artifact
                else RecommendedContentFormat.TEXT_POST
            ),
            forbidden_formats=[],
            deterministic_allowed=True,
            ai_image_allowed=has_concrete_artifact,
            judge="written-content-judge",
            rationale=(
                "Founder stories can use a visual only when a concrete artifact anchors the scene."
                if has_concrete_artifact
                else "Founder stories usually earn trust through specific writing."
            ),
        )

    if _has_metaphor_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.METAPHOR,
            needs_visual=True,
            reason=VisualNeedReason.VISUAL_CARRIES_METAPHOR,
            recommended_format=RecommendedContentFormat.AI_GENERATED_IMAGE,
            forbidden_formats=[],
            deterministic_allowed=False,
            ai_image_allowed=True,
            judge="visual-content-judge",
            rationale="A single concrete metaphor can justify AI image generation.",
        )

    if _has_lesson_signal(lowered):
        return ContentJobPlan(
            job_type=ContentJobType.LESSON,
            needs_visual=False,
            reason=VisualNeedReason.NO_VISUAL_NEEDED,
            recommended_format=RecommendedContentFormat.TEXT_POST,
            forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
            deterministic_allowed=False,
            ai_image_allowed=False,
            judge="written-content-judge",
            rationale="Lessons should stand on the writing unless structure or proof is present.",
        )

    return ContentJobPlan(
        job_type=ContentJobType.OPINION,
        needs_visual=False,
        reason=VisualNeedReason.NO_VISUAL_NEEDED,
        recommended_format=RecommendedContentFormat.TEXT_POST,
        forbidden_formats=[RecommendedContentFormat.AI_GENERATED_IMAGE],
        deterministic_allowed=False,
        ai_image_allowed=False,
        judge="written-content-judge",
        rationale="No data, workflow, product state, framework, or concrete metaphor signal was detected.",
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
                for key in (
                    "refined_text",
                    "text",
                    "topic",
                    "headline",
                    "intended_takeaway",
                    "content_type",
                )
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
            for key in ("refined_text", "topic", "headline", "intended_takeaway", "content_type")
        )
        + f" {visual_prompt or ''}"
    )


def _has_data_signal(lowered: str) -> bool:
    return bool(
        "%" in lowered
        or "$" in lowered
        or re.search(
            r"\b(metric|data|chart|benchmark|rank|ranking|compare|versus|vs|percent|rate|cost|revenue|ctr|engagement)\b",
            lowered,
        )
        or re.search(r"\b\d+(?:\.\d+)?x\b", lowered)
    )


def _looks_like_text_only_thesis(lowered: str) -> bool:
    words = lowered.split()
    return bool(
        len(words) <= 18
        and any(signal in lowered for signal in (" is not ", " isn't ", "not the "))
        and not any(signal in lowered for signal in ("step", "stages", "chart", "%", "$", " vs "))
    )


def _has_workflow_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(workflow|pipeline|process|system|handoff|sequence|loop|cycle|routing|route|capture|extract|refine|render|judge|orchestration|agent|agents)\b",
            lowered,
        )
        or "->" in lowered
    )


def _has_framework_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(framework|playbook|checklist|steps|layers|matrix|taxonomy|principles|rules|carousel|carousels|document|documents|saveable|template|templates|formats|content systems|brand formats)\b",
            lowered,
        )
    )


def _has_product_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(product|feature|release|demo|screen|ui|dashboard|queue|interface|workbench|surface|pilaster|genpeli|invoz|holus)\b",
            lowered,
        )
        or "decision surface" in lowered
    )


def _has_founder_story_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(i built|i learned|i realized|founder|operator|customer|client|voice note|behind the scenes|story)\b",
            lowered,
        )
    )


def _has_metaphor_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(metaphor|like a|as if|buried|pile|bridge|compass|map|mirror|signal|noise|trap|lens)\b",
            lowered,
        )
    )


def _has_lesson_signal(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(lesson|learned|observation|takeaway|opinion|contrarian|mistake|truth|note)\b",
            lowered,
        )
    )
