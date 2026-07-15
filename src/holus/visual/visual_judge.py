"""Visual quality gate and retry instructions for dispatched assets.

This module is intentionally deterministic. It validates the generated file
and the production contract, then emits route-specific retry guidance. It does
not claim semantic image understanding; a vision-model judge can implement the
same decision contract later.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from holus.visual.proximity_router import VisualConceptRoute, VisualProximityMode

if TYPE_CHECKING:
    from pathlib import Path

    from holus.visual.production_plan import VisualProductionPlan


class VisualJudgeVerdict(StrEnum):
    """Deterministic visual gate verdict."""

    PASS = "pass"
    RETRY = "retry"
    FAIL = "fail"


class VisualJudgeDecision(BaseModel):
    """Auditable quality decision for one generated visual attempt."""

    verdict: VisualJudgeVerdict
    score: float = Field(ge=0.0, le=1.0)
    route_mode: VisualProximityMode | None = None
    reasons: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    retry_instruction: str | None = None
    requires_human_review: bool = False
    semantic_scope: str = "deterministic_file_and_plan_gate"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def log_summary(self) -> dict[str, Any]:
        """Return compact judge metadata for JSONL logs."""
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "route_mode": self.route_mode.value if self.route_mode else None,
            "requires_human_review": self.requires_human_review,
            "failed_checks": self.failed_checks,
            "retry_instruction": self.retry_instruction,
            "semantic_scope": self.semantic_scope,
        }


def judge_visual_output(
    *,
    output_path: Path | None,
    expected_width: int,
    expected_height: int,
    asset_kind: str,
    route: VisualConceptRoute | None = None,
    plan: VisualProductionPlan | None = None,
    result_metadata: dict[str, Any] | None = None,
) -> VisualJudgeDecision:
    """Judge a generated output with deterministic checks.

    FACT: this checks file existence, readability, coarse dimensions, and the
    presence of route/plan contracts.
    FACT: it does not inspect whether the pixels semantically match the idea.
    """
    passed: list[str] = []
    failed: list[str] = []
    reasons: list[str] = []
    metadata: dict[str, Any] = {
        "expected_dimensions": [expected_width, expected_height],
        "asset_kind": asset_kind,
        "result_metadata": result_metadata or {},
    }

    if output_path is None:
        return _fail("Provider did not return an output path.", route, metadata)
    metadata["output_path"] = str(output_path)

    if not output_path.exists():
        return _fail(f"Output file does not exist: {output_path}", route, metadata)
    passed.append("output_file_exists")
    metadata["file_bytes"] = output_path.stat().st_size
    if output_path.stat().st_size <= 0:
        return _fail("Output file is empty.", route, metadata, passed=passed)
    passed.append("output_file_nonempty")

    suffix = output_path.suffix.lower()
    if suffix == ".pdf":
        if output_path.stat().st_size < 8:
            return _fail("PDF output is too small to be usable.", route, metadata, passed=passed)
        passed.append("pdf_file_present")
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        image_check = _inspect_image(output_path)
        metadata.update(image_check["metadata"])
        if image_check["failed"]:
            return _fail(
                image_check["failed"],
                route,
                metadata,
                passed=passed,
                failed=["image_open_failed"],
            )
        passed.append("image_file_readable")
        width = int(metadata["actual_dimensions"][0])
        height = int(metadata["actual_dimensions"][1])
        if width < int(expected_width * 0.8) or height < int(expected_height * 0.8):
            failed.append("image_dimensions_too_small")
            reasons.append(
                f"Image dimensions {width}x{height} are too small for requested "
                f"{expected_width}x{expected_height}."
            )
    else:
        failed.append("unknown_output_extension")
        reasons.append(f"Output extension is not a known image/PDF format: {suffix or '<none>'}.")

    if route is None:
        failed.append("missing_visual_route")
        reasons.append("No proximity route was attached, so creative intent cannot be audited.")
    else:
        passed.append("visual_route_attached")
        metadata["route_mode"] = route.mode.value

    if plan is None:
        failed.append("missing_visual_plan")
        reasons.append("No production plan was attached, so provider compliance cannot be audited.")
    else:
        passed.append("visual_plan_attached")
        metadata["plan_id"] = plan.plan_id
        if not plan.required_elements:
            failed.append("plan_has_no_required_elements")
        if not plan.compliance_checks:
            failed.append("plan_has_no_compliance_checks")

    if failed:
        retry_instruction = build_retry_instruction(route, plan, reasons)
        return VisualJudgeDecision(
            verdict=VisualJudgeVerdict.RETRY,
            score=0.55,
            route_mode=route.mode if route else None,
            reasons=reasons or ["Deterministic quality gate found retryable issues."],
            passed_checks=passed,
            failed_checks=failed,
            retry_instruction=retry_instruction,
            requires_human_review=True,
            metadata=metadata,
        )

    return VisualJudgeDecision(
        verdict=VisualJudgeVerdict.PASS,
        score=0.82,
        route_mode=route.mode if route else None,
        reasons=[
            "File is readable and the route/production plan contract is attached.",
            "Semantic visual quality still requires human or vision-model review.",
        ],
        passed_checks=passed,
        failed_checks=[],
        requires_human_review=False,
        metadata=metadata,
    )


def mutate_visual_plan_for_retry(
    plan: VisualProductionPlan,
    decision: VisualJudgeDecision,
    *,
    attempt: int,
) -> VisualProductionPlan:
    """Strengthen a production plan after a judge retry verdict."""
    instruction = decision.retry_instruction or build_retry_instruction(
        None, plan, decision.reasons
    )
    return plan.model_copy(
        update={
            "plan_id": f"{plan.plan_id}__retry{attempt}",
            "scene_script": f"{plan.scene_script} Retry correction: {instruction}",
            "composition_script": (
                f"{plan.composition_script} Make the required elements larger, clearer, "
                "and closer to the center of the frame."
            ),
            "required_elements": [
                *plan.required_elements,
                "retry correction must be visibly resolved",
            ],
            "forbidden_elements": [
                *plan.forbidden_elements,
                "ambiguous scene that requires the caption to explain it",
            ],
            "compliance_checks": [
                *plan.compliance_checks,
                "Did the retry correction visibly resolve the prior judge issue?",
            ],
        }
    )


def build_retry_instruction(
    route: VisualConceptRoute | None,
    plan: VisualProductionPlan | None,
    reasons: list[str],
) -> str:
    """Build route-specific retry guidance for the next provider attempt."""
    mode = route.mode if route else plan.route_mode if plan else None
    reason_text = " ".join(reasons).strip()
    prefix = f"Fix these gate issues: {reason_text}. " if reason_text else ""
    if mode == VisualProximityMode.WORKFLOW:
        return (
            prefix + "Make the sequence literal: five distinct stages, one visible handoff path, "
            "one bottleneck, and one model/component inside the process."
        )
    if mode == VisualProximityMode.CHART:
        return (
            prefix
            + "Use one chart only, one highlighted comparison/anomaly, and remove decorative data clutter."
        )
    if mode == VisualProximityMode.PERSON_STORY:
        return (
            prefix
            + "Show one decision-maker reacting to one concrete artifact; make the gesture, mark, "
            "or choice visible."
        )
    if mode == VisualProximityMode.OBJECT_METAPHOR:
        return (
            prefix
            + "Use one physical metaphor object with a clear tension or imbalance; remove competing metaphors."
        )
    if mode == VisualProximityMode.PRODUCT_SCENE:
        return (
            prefix
            + "Show one selected item, one reason or fit signal, and one decision state in a plausible UI."
        )
    if mode == VisualProximityMode.TYPOGRAPHY_CARD:
        return prefix + "Use only the planned thesis and one support line with clear hierarchy."
    return prefix + "Make the main idea concrete, singular, and visually legible."


def _inspect_image(output_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image

        with Image.open(output_path) as image:
            image.verify()
        with Image.open(output_path) as image:
            return {
                "failed": None,
                "metadata": {
                    "actual_dimensions": [image.width, image.height],
                    "image_mode": image.mode,
                    "image_format": image.format,
                },
            }
    except Exception as exc:  # pragma: no cover - exact PIL exception varies by format.
        return {"failed": f"Image file is not readable: {exc}", "metadata": {}}


def _fail(
    reason: str,
    route: VisualConceptRoute | None,
    metadata: dict[str, Any],
    *,
    passed: list[str] | None = None,
    failed: list[str] | None = None,
) -> VisualJudgeDecision:
    return VisualJudgeDecision(
        verdict=VisualJudgeVerdict.FAIL,
        score=0.0,
        route_mode=route.mode if route else None,
        reasons=[reason],
        passed_checks=passed or [],
        failed_checks=failed or ["output_invalid"],
        retry_instruction=build_retry_instruction(route, None, [reason]),
        requires_human_review=True,
        metadata=metadata,
    )
