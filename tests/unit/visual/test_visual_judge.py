"""Tests for deterministic visual judge contracts."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from holus.visual.production_plan import build_visual_production_plan
from holus.visual.proximity_router import choose_visual_concept_route
from holus.visual.visual_judge import (
    VisualJudgeVerdict,
    judge_visual_output,
    mutate_visual_plan_for_retry,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_visual_judge_passes_readable_image_with_route_and_plan(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.png"
    output_path.write_bytes(_png_bytes(1024, 1024))
    source = {
        "piece_id": "chart-1",
        "topic": "Conversion improved by 32%",
        "refined_text": "The carousel format outperformed the single image by 32%.",
    }
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)

    decision = judge_visual_output(
        output_path=output_path,
        expected_width=1024,
        expected_height=1024,
        asset_kind="single_image",
        route=route,
        plan=plan,
    )

    assert decision.verdict == VisualJudgeVerdict.PASS
    assert decision.requires_human_review is False
    assert "image_file_readable" in decision.passed_checks
    assert decision.metadata["actual_dimensions"] == [1024, 1024]


def test_visual_judge_fails_unreadable_image(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.png"
    output_path.write_bytes(b"not-a-real-png")

    decision = judge_visual_output(
        output_path=output_path,
        expected_width=1024,
        expected_height=1024,
        asset_kind="single_image",
    )

    assert decision.verdict == VisualJudgeVerdict.FAIL
    assert decision.requires_human_review is True
    assert "image_open_failed" in decision.failed_checks


def test_visual_judge_retries_when_plan_context_is_missing(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.png"
    output_path.write_bytes(_png_bytes(1024, 1024))

    decision = judge_visual_output(
        output_path=output_path,
        expected_width=1024,
        expected_height=1024,
        asset_kind="single_image",
    )

    assert decision.verdict == VisualJudgeVerdict.RETRY
    assert decision.requires_human_review is True
    assert "missing_visual_route" in decision.failed_checks
    assert "missing_visual_plan" in decision.failed_checks


def test_mutate_visual_plan_for_retry_strengthens_contract(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.png"
    output_path.write_bytes(_png_bytes(200, 200))
    source = {
        "piece_id": "workflow-1",
        "topic": "The harness is the workflow",
        "refined_text": "Planning, execution, review, and fallback need separate jobs.",
    }
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)
    decision = judge_visual_output(
        output_path=output_path,
        expected_width=1024,
        expected_height=1024,
        asset_kind="single_image",
        route=route,
        plan=plan,
    )

    retry_plan = mutate_visual_plan_for_retry(plan, decision, attempt=2)

    assert decision.verdict == VisualJudgeVerdict.RETRY
    assert retry_plan.plan_id.endswith("__retry2")
    assert "Retry correction:" in retry_plan.scene_script
    assert "retry correction must be visibly resolved" in retry_plan.required_elements


def _png_bytes(width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(240, 240, 240)).save(buffer, format="PNG")
    return buffer.getvalue()
