"""Tests for content job planning and visual necessity gates."""

from __future__ import annotations

from holus.visual.content_job import (
    ContentJobType,
    RecommendedContentFormat,
    VisualNeedReason,
    plan_content_job,
)


def test_opinion_routes_to_text_only() -> None:
    plan = plan_content_job(
        {
            "refined_text": "The model is not the workflow. The harness is.",
            "topic": "Builder opinion",
        }
    )

    assert plan.job_type == ContentJobType.OPINION
    assert plan.needs_visual is False
    assert plan.recommended_format == RecommendedContentFormat.TEXT_POST
    assert plan.ai_image_allowed is False


def test_data_claim_forbids_ai_image() -> None:
    plan = plan_content_job(
        {
            "refined_text": "Document posts reached 12.4% engagement while image posts reached 1.9%.",
            "topic": "LinkedIn format benchmark",
        }
    )

    assert plan.job_type == ContentJobType.DATA_CLAIM
    assert plan.needs_visual is True
    assert plan.reason == VisualNeedReason.VISUAL_PROVES_DATA
    assert plan.recommended_format == RecommendedContentFormat.TEXT_WITH_DETERMINISTIC_VISUAL
    assert RecommendedContentFormat.AI_GENERATED_IMAGE in plan.forbidden_formats


def test_workflow_routes_to_carousel_or_deterministic_visual() -> None:
    plan = plan_content_job(
        {
            "refined_text": "The pipeline works when planning, execution, review, and fallback each get a lane.",
            "topic": "Workflow explanation",
        }
    )

    assert plan.job_type == ContentJobType.WORKFLOW_EXPLANATION
    assert plan.needs_visual is True
    assert plan.recommended_format == RecommendedContentFormat.CAROUSEL_DOCUMENT
    assert plan.deterministic_allowed is True
    assert plan.ai_image_allowed is False


def test_metaphor_allows_ai_image() -> None:
    plan = plan_content_job(
        {
            "refined_text": "A pile of notes can bury the one card that changes the decision.",
            "topic": "Metaphor",
        }
    )

    assert plan.job_type == ContentJobType.METAPHOR
    assert plan.needs_visual is True
    assert plan.recommended_format == RecommendedContentFormat.AI_GENERATED_IMAGE
    assert plan.ai_image_allowed is True


def test_founder_story_needs_artifact_before_visual() -> None:
    text_only = plan_content_job({"refined_text": "I learned this after a hard week building."})
    artifact = plan_content_job(
        {"refined_text": "The founder points at one marked sentence in the voice note."}
    )

    assert text_only.job_type == ContentJobType.FOUNDER_STORY
    assert text_only.needs_visual is False
    assert artifact.job_type == ContentJobType.FOUNDER_STORY
    assert artifact.needs_visual is True
    assert artifact.reason == VisualNeedReason.VISUAL_SUPPORTS_STORY
