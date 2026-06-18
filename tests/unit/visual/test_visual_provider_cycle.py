"""Tests for visual provider cycle helpers."""

from __future__ import annotations

from scripts.visual_provider_cycle import (
    build_ai_image_direction,
    build_cycle_prompt,
    build_improvement_plan,
    improvement_directives_from_history,
    load_prior_reports,
    next_improvements,
    parse_provider_model,
    prompt_digest,
    ranked_provider_models,
    score_result,
    slug,
    summarize_results,
    write_example_plan_batch,
)

from holus.visual.dispatcher import RefinedVisualSource, VisualDispatchStatus, VisualProvider
from holus.visual.production_plan import build_visual_production_plan
from holus.visual.proximity_router import choose_visual_concept_route


def test_parse_provider_model_with_default_model() -> None:
    provider, model = parse_provider_model("agy_cli_image:default")

    assert provider == VisualProvider.AGY_CLI_IMAGE
    assert model is None


def test_parse_provider_model_with_named_model() -> None:
    provider, model = parse_provider_model("agy_cli_image:Gemini 3.5 Flash (Medium)")

    assert provider == VisualProvider.AGY_CLI_IMAGE
    assert model == "Gemini 3.5 Flash (Medium)"


def test_slug_makes_model_label_filesystem_safe() -> None:
    assert (
        slug("agy_cli_image-Gemini 3.5 Flash (Medium)") == "agy_cli_image-gemini-3.5-flash-medium"
    )


def test_next_improvements_uses_judge_reasons() -> None:
    improvements = next_improvements(
        {
            "verdict": "retry",
            "reasons": ["image size mismatch", "missing workflow stages"],
        }
    )

    assert improvements == [
        "Tighten production plan for: image size mismatch",
        "Tighten production plan for: missing workflow stages",
    ]


def test_build_cycle_prompt_injects_prior_directives() -> None:
    source = RefinedVisualSource(
        piece_id="cycle-1",
        platform="linkedin",
        content_type="image_post",
        refined_text="One model per lane improves the workflow.",
    )

    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)
    direction = build_ai_image_direction(
        source,
        route=route,
        plan=plan,
        platform="linkedin",
        width=1080,
        height=1350,
    )

    prompt = build_cycle_prompt(
        source,
        ["Make the handoff path visible."],
        image_direction=direction,
    )

    assert "SOURCE OF TRUTH: refined Holus content" in prompt
    assert "AI IMAGE DIRECTOR STRUCTURED BRIEF" in prompt
    assert '"viewer_takeaway"' in prompt
    assert '"negative_prompt"' in prompt
    assert "Prior visual-cycle lessons" in prompt
    assert "Make the handoff path visible." in prompt


def test_prompt_digest_is_stable() -> None:
    prompt = "same structured prompt"

    assert prompt_digest(prompt) == prompt_digest(prompt)
    assert prompt_digest(prompt) != prompt_digest("different structured prompt")


def test_write_example_plan_batch_creates_10_shared_prompt_packages(tmp_path) -> None:
    class Args:
        output_dir = str(tmp_path)
        platform = "linkedin"
        width = 768
        height = 768

    manifest = write_example_plan_batch(Args())

    assert manifest["total_thoughts"] == 10
    assert manifest["total_provider_versions"] == 20
    assert (tmp_path / "structured-batch-manifest.json").exists()
    for item in manifest["items"]:
        provider_hashes = {
            provider["structured_prompt_hash"] for provider in item["provider_prompts"]
        }
        assert provider_hashes == {item["structured_prompt_hash"]}
        assert len(item["provider_prompts"]) == 2


def test_improvement_directives_from_history_deduplicates_and_bounds() -> None:
    reports = [
        {
            "improvement_plan": {
                "next_cycle_directives": [
                    "Make the handoff path visible.",
                    "Make the handoff path visible.",
                    "Avoid fake UI labels.",
                ]
            }
        },
        {"improvement_plan": {"next_cycle_directives": ["Use one chart only."]}},
    ]

    assert improvement_directives_from_history(reports) == [
        "Make the handoff path visible.",
        "Avoid fake UI labels.",
        "Use one chart only.",
    ]


def test_load_prior_reports_reads_newest_first(tmp_path) -> None:
    older = tmp_path / "older"
    newer = tmp_path / "newer"
    older.mkdir()
    newer.mkdir()
    (older / "cycle-report.json").write_text('{"cycle_id": "older"}', encoding="utf-8")
    (newer / "cycle-report.json").write_text('{"cycle_id": "newer"}', encoding="utf-8")

    reports = load_prior_reports(tmp_path, limit=2)

    assert {report["cycle_id"] for report in reports} == {"older", "newer"}


def test_score_result_and_ranking_prefer_passing_outputs() -> None:
    assert score_result(VisualDispatchStatus.FAILED.value, {"verdict": "pass"}) == 0
    assert score_result(VisualDispatchStatus.SUCCEEDED.value, {"verdict": "pass"}) == 100
    assert score_result(VisualDispatchStatus.SUCCEEDED.value, {"verdict": "retry"}) == 55

    ranked = ranked_provider_models(
        [
            {
                "provider": "agy_cli_image",
                "model": "default",
                "score": 55,
                "status": "succeeded",
                "output_path": "agy.png",
                "duration_ms": 100,
            },
            {
                "provider": "codex_cli_image",
                "model": "default",
                "score": 100,
                "status": "succeeded",
                "output_path": "codex.png",
                "duration_ms": 200,
            },
        ]
    )

    assert ranked[0]["provider"] == "codex_cli_image"


def test_build_improvement_plan_carries_failure_actions() -> None:
    plan = build_improvement_plan(
        [
            {
                "provider": "agy_cli_image",
                "model": "default",
                "score": 55,
                "status": "succeeded",
                "output_path": "agy.png",
                "duration_ms": 100,
                "next_improvements": ["Tighten production plan for: missing workflow stages"],
            }
        ],
        ["Avoid fake UI labels."],
    )

    assert plan["manual_review_required"] is True
    assert plan["carried_forward_directives"] == ["Avoid fake UI labels."]
    assert plan["next_cycle_directives"] == ["Tighten production plan for: missing workflow stages"]


def test_summarize_results_picks_first_success() -> None:
    summary = summarize_results(
        [
            {
                "provider": "agy_cli_image",
                "model": "default",
                "status": VisualDispatchStatus.FAILED.value,
                "output_path": None,
                "score": 0,
            },
            {
                "provider": "codex_cli_image",
                "model": "gpt-5.5",
                "status": VisualDispatchStatus.SUCCEEDED.value,
                "output_path": "asset.png",
                "score": 100,
            },
        ]
    )

    assert summary["total"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert summary["best_available"] == {
        "provider": "codex_cli_image",
        "model": "gpt-5.5",
        "output_path": "asset.png",
    }
    assert summary["ranked_provider_models"][0]["provider"] == "codex_cli_image"
