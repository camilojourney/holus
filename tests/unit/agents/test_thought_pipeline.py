"""Tests for Holus Thought Studio deterministic pipeline helpers."""

from pathlib import Path

import pytest
import yaml

from holus.agents.marketing.creative_strategy import (
    choose_creative_strategy,
    editorial_card_copy,
)
from holus.agents.marketing.thought_pipeline import (
    ThoughtContentPipeline,
    _brand_identity,
    _brief_from_profile,
    _build_platform_text,
    _carousel_outline_from_thought,
    _carousel_visual_spec_from_outline,
    _extract_thought_essence,
    _prepare_judged_carousel_outline,
    _prepare_judged_visual_spec,
    _select_visual_brief,
    _visual_spec_from_thought,
    build_posting_destination,
)

AI_WORKFLOW_THOUGHT = """
On my AI little workflow I used
Claude to plan
Codex to let the plan run for hours or days

On the plans I use multiple skills (the hands)
Skills are running with multiple models for knowledge diversity and accuracy.

Gpt 5.5 for coding
Agy (antigravity cli) to review
Deepseek for fallbacks and evaluations
Claude 4.6 for consulting skills.

Now harness
1. Cursor for daily work.
2. Codex for app development since it can control your computer and debug faster
3. Claude code extension for cursor to planner.

Plans
Codex 200
Claude 20
Agy 20
Deepseek 20 (roughly, I am just testing it)
Cursor 60
"""


@pytest.mark.asyncio
async def test_persisted_records_include_package_metadata(tmp_path: Path) -> None:
    pipeline = ThoughtContentPipeline(
        queue_dir=tmp_path / "queue",
        rendered_dir=tmp_path / "rendered",
    )

    content_set = await pipeline.create_content_set(
        thought=AI_WORKFLOW_THOUGHT,
        channels=["linkedin_text"],
    )

    [record] = content_set.records
    persisted = yaml.safe_load(
        (tmp_path / "queue" / f"{record['piece_id']}.yaml").read_text(encoding="utf-8")
    )
    assert persisted["platform_job_plan"] == record["platform_job_plan"]
    assert persisted["quality"]["platform_fit"] == record["quality"]["platform_fit"]


@pytest.mark.asyncio
async def test_failed_platform_fit_blocks_human_review(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "holus.agents.marketing.thought_pipeline._platform_fit",
        lambda _record: {"verdict": "REVIEW"},
    )
    pipeline = ThoughtContentPipeline(
        queue_dir=tmp_path / "queue",
        rendered_dir=tmp_path / "rendered",
    )

    content_set = await pipeline.create_content_set(
        thought=AI_WORKFLOW_THOUGHT,
        channels=["linkedin_text"],
        write_records=False,
    )

    assert content_set.package["quality_evaluation"]["ready_for_human_review"] is False
    checklist = content_set.package["approval_workflow"]["review_checklist"]
    platform_fit_item = next(
        item for item in checklist if item["artifact"] == "quality_evaluation.platform_fit_summary"
    )
    assert platform_fit_item["status"] == "FAIL"
    assert "1 failed" in platform_fit_item["evidence"]


def test_extracts_ai_workflow_essence() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)

    assert essence.thesis == "The model is not the workflow. The harness is the workflow."
    assert "Skills act like the hands." in essence.role_map
    assert "Multiple models add knowledge diversity and catch blind spots." in essence.role_map
    assert "Codex: 200" in essence.evidence
    assert "Cursor: 60" in essence.evidence
    assert "Claude: 20" in essence.evidence
    assert "Claude: 4" not in essence.evidence
    assert essence.mode == "builder note"


def test_linkedin_text_uses_essence_not_raw_dump() -> None:
    text = _build_platform_text(AI_WORKFLOW_THOUGHT, "linkedin_text")

    assert "The model is not the workflow. The harness is the workflow." in text
    assert "Do not ask one model to be the whole company." in text
    assert "The raw thought was this" not in text
    assert "On my AI little workflow" not in text
    assert "Codex: 200" in text


def test_twitter_thread_stays_platform_native() -> None:
    text = _build_platform_text(AI_WORKFLOW_THOUGHT, "twitter_x_thread")

    tweets = [part.strip() for part in text.split("\n\n") if part.strip()]
    assert len(tweets) == 5
    assert tweets[0].startswith("1/ The model is not the workflow")
    assert all(len(tweet) <= 280 for tweet in tweets)


def test_visual_copy_uses_workflow_harness_not_generic_signal() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    strategy = choose_creative_strategy(
        essence.visual_prompt,
        channel="instagram_image",
        nonce="test",
    )
    copy = editorial_card_copy(essence.visual_prompt, strategy)

    assert strategy.strategy_id == "ai_workflow_harness_card"
    assert strategy.hook_pattern == "harness thesis"
    assert strategy.visual_metaphor == "orchestrated harness instead of isolated model"
    assert copy["label"] == "Workflow harness"
    assert copy["emphasis_word"] == "The harness"
    assert "Give each model a job." in copy["proof_points"]
    assert "One clear idea." not in copy["proof_points"]


def test_visual_spec_explains_variables_and_blocks_raw_transcript_copy() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    brief = _select_visual_brief(essence.visual_prompt, "instagram_image", "test-group")
    spec = _visual_spec_from_thought(essence.visual_prompt, brief)

    rendered_copy = " ".join(
        [
            str(spec["label"]),
            str(spec["hook"]),
            str(spec["subhook"]),
            str(spec["emphasis_word"]),
            " ".join(spec["proof_points"]),
        ]
    )

    assert "On my AI little workflow" not in rendered_copy
    assert "The Signal" not in rendered_copy
    assert spec["hook"] == "The model is not the workflow"
    assert spec["style_profile"]["profile_id"] == "ai-workflow-harness"
    assert spec["prompt_contract"]["subject"].startswith("Claude planning")
    assert spec["creative_contract"]["strategy_id"] == "ai_workflow_harness_card"
    assert spec["variable_rationale"]["lineage"].startswith("raw thought -> thought_essence")
    assert "system roles" in spec["variable_rationale"]["proof_points"]
    assert spec["brand_identity"]["brand_handle"] is None
    assert spec["brand_identity"]["available_handles"]["en"] == "@camiloexperience"
    assert spec["brand_identity"]["available_handles"]["es"] == "@camilojourney"


def test_carousel_uses_harness_profile_and_rationale() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    brief = _select_visual_brief(essence.visual_prompt, "linkedin_carousel", "test-group")
    outline = _carousel_outline_from_thought(essence.visual_prompt, brief, "linkedin_carousel")

    assert outline["style_profile"]["profile_id"] == "ai-workflow-harness"
    assert outline["style_profile"]["motif"] == "multi-model harness"
    assert outline["creative_contract"]["strategy_id"] == "ai_workflow_harness_card"
    assert outline["variable_rationale"]["model_provider"].startswith(
        "holus/deterministic-thought-pipeline"
    )
    assert outline["brand_identity"]["brand_handle"] is None


def test_brand_identity_can_include_language_handle_when_opted_in() -> None:
    assert (
        _brand_identity(language="en", include_handle=True)["brand_handle"] == "@camiloexperience"
    )
    assert _brand_identity(language="es", include_handle=True)["brand_handle"] == "@camilojourney"
    assert _brand_identity(language="en", include_handle=False)["brand_handle"] is None


def test_posting_destination_routes_by_language_and_platform() -> None:
    english = build_posting_destination(
        platform="instagram",
        thought="The model is not the workflow. The harness is the workflow.",
    )
    spanish = build_posting_destination(
        platform="instagram",
        thought="El flujo de trabajo necesita planes, revisión y fallback.",
    )

    assert english["handle"] == "@camiloexperience"
    assert english["profile_url"] == "https://instagram.com/camiloexperience"
    assert english["approval_required"] is True
    assert spanish["handle"] == "@camilojourney"
    assert spanish["language"] == "es"


def test_visual_judge_redoes_generic_workflow_image() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    wrong_brief = _brief_from_profile(
        "editorial-thesis-card",
        seed_material="force-wrong-image-brief",
    )

    spec, final_brief, judge = _prepare_judged_visual_spec(
        AI_WORKFLOW_THOUGHT,
        essence,
        "instagram_image",
        wrong_brief,
    )

    assert judge.verdict == "PASS"
    assert judge.redo_count == 1
    assert final_brief.profile_id == "ai-workflow-harness"
    assert spec["creative_contract"]["strategy_id"] == "ai_workflow_harness_card"
    assert spec["hook"] == "The model is not the workflow"


def test_visual_judge_redoes_generic_workflow_carousel() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    wrong_brief = _brief_from_profile(
        "ai-focus-thesis",
        seed_material="force-wrong-carousel-brief",
    )

    outline, final_brief, judge = _prepare_judged_carousel_outline(
        AI_WORKFLOW_THOUGHT,
        essence,
        "linkedin_carousel",
        wrong_brief,
    )

    assert judge.verdict == "PASS"
    assert judge.redo_count == 1
    assert final_brief.profile_id == "ai-workflow-harness"
    assert outline["slides"][0]["variables"]["headline"] == "The model is not the workflow"
    assert outline["creative_contract"]["strategy_id"] == "ai_workflow_harness_card"


def test_instagram_carousel_uses_platform_export_metadata() -> None:
    essence = _extract_thought_essence(AI_WORKFLOW_THOUGHT)
    brief = _select_visual_brief(essence.visual_prompt, "instagram_carousel", "test-group")

    outline, final_brief, judge = _prepare_judged_carousel_outline(
        AI_WORKFLOW_THOUGHT,
        essence,
        "instagram_carousel",
        brief,
    )
    spec = _carousel_visual_spec_from_outline(
        outline,
        final_brief,
        "instagram_carousel",
        judge,
        renderer="holus/carousel-renderer",
    )

    assert judge.verdict == "PASS"
    assert spec["platform_export"] == "instagram_multi_image_carousel"
    assert spec["review_artifact"] == "pdf"
    assert len(spec["carousel_slides"]) == 5


@pytest.mark.asyncio
async def test_linkedin_image_uses_refined_visual_source(tmp_path, monkeypatch) -> None:
    def fake_render_visual(visual_spec, output_path):
        output_path.write_bytes(b"PNG_BYTES")
        return True

    monkeypatch.setattr(
        "holus.agents.marketing.visual_pipeline._render_visual",
        fake_render_visual,
    )

    pipeline = ThoughtContentPipeline(
        queue_dir=tmp_path / "queue",
        rendered_dir=tmp_path / "rendered",
    )
    content_set = await pipeline.create_content_set(
        thought=AI_WORKFLOW_THOUGHT,
        channels=["linkedin_image"],
    )

    [record] = content_set.records
    assert record["platform"] == "linkedin"
    assert record["content_type"] == "image_post"
    assert record["rendered_image_path"].endswith(".png")
    assert (tmp_path / "rendered" / f"{record['piece_id']}.png").read_bytes() == b"PNG_BYTES"

    source = record["visual_spec"]["refined_visual_source"]
    assert source["platform"] == "linkedin"
    assert source["content_type"] == "image_post"
    assert source["refined_text"] == record["text"]
    assert source["raw_thought_provenance"].startswith("On my AI little workflow")
    assert "On my AI little workflow" not in source["refined_text"]
    route = record["visual_spec"]["visual_route"]
    assert route["mode"] == "workflow"
    assert route["use_workflow"] is True
    assert route["use_person"] is False
    assert "role separation" in " ".join(route["visual_do"])
    plan = record["visual_spec"]["visual_plan"]
    assert plan["route_mode"] == "workflow"
    assert plan["viewer_test"]
    assert plan["compliance_checks"]
    strategy = record["visual_spec"]["visual_strategy"]
    assert strategy["rendering_path"] == "deterministic_template"
    assert strategy["provider"] == "html_renderer"
    assert strategy["template_kind"] == "operating_map"
    assert strategy["design_system"]["palette"]
