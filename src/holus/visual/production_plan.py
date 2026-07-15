"""Deterministic visual production plans built after proximity routing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from holus.visual.linkedin_lens import apply_linkedin_impact_lens
from holus.visual.proximity_router import VisualConceptRoute, VisualProximityMode


class VisualProductionPlan(BaseModel):
    """Detailed provider contract for one visual generation attempt."""

    plan_id: str
    route_mode: VisualProximityMode
    concept: str
    viewer_test: str
    scene_script: str
    composition_script: str
    required_elements: list[str] = Field(default_factory=list)
    text_policy: str
    forbidden_elements: list[str] = Field(default_factory=list)
    compliance_checks: list[str] = Field(default_factory=list)

    def prompt_contract(self) -> str:
        """Return a generation-ready plan block."""
        return (
            "Production plan:\n"
            f"Plan id: {self.plan_id}\n"
            f"Route mode: {self.route_mode.value}\n"
            f"Concept: {self.concept}\n"
            f"Viewer test: {self.viewer_test}\n"
            f"Scene script: {self.scene_script}\n"
            f"Composition script: {self.composition_script}\n"
            f"Required elements: {'; '.join(self.required_elements)}\n"
            f"Text policy: {self.text_policy}\n"
            f"Forbidden elements: {'; '.join(self.forbidden_elements)}\n"
            f"Compliance checks: {'; '.join(self.compliance_checks)}"
        )

    def log_summary(self) -> dict[str, Any]:
        """Return compact plan metadata for logs."""
        return {
            "plan_id": self.plan_id,
            "route_mode": self.route_mode.value,
            "concept": self.concept,
            "viewer_test": self.viewer_test,
        }


def build_visual_production_plan(
    source: Any,
    route: VisualConceptRoute,
) -> VisualProductionPlan:
    """Build a deterministic production script from source + route."""
    takeaway = _takeaway(source, route.viewer_takeaway)
    plan_id = f"{_piece_id(source)}__{route.mode.value}__v1"
    common_forbidden = [
        *route.visual_dont,
        "unexplained decorative objects",
        "stock-photo handshake",
        "fake brand logos",
        "watermarks",
        "random dashboard widgets",
    ]

    if route.mode == VisualProximityMode.WORKFLOW:
        return _with_linkedin_lens(
            VisualProductionPlan(
                plan_id=plan_id,
                route_mode=route.mode,
                concept=f"Show the operating sequence behind: {takeaway}",
                viewer_test="A viewer should be able to name the sequence and the bottleneck without reading the caption.",
                scene_script=(
                    "A clean operating board where each step is a distinct station. The system should "
                    "feel planned, not magical."
                ),
                composition_script=(
                    "Five visible stages arranged left-to-right with a single flow direction. Put the "
                    "small model/component inside the flow, not as the hero."
                ),
                required_elements=[
                    "five distinct process stages",
                    "one visible handoff path",
                    "one small model/component as part of the system",
                    "clear before/after or input/output boundary",
                ],
                text_policy=(
                    "Readable labels are allowed only for exact stage names from the plan. No random UI text."
                ),
                forbidden_elements=common_forbidden,
                compliance_checks=[
                    "Does the image show a sequence?",
                    "Is each job visually separate?",
                    "Is the model only one part of the system?",
                ],
            ),
            route,
            source,
        )

    if route.mode == VisualProximityMode.CHART:
        return _with_linkedin_lens(
            VisualProductionPlan(
                plan_id=plan_id,
                route_mode=route.mode,
                concept=f"Turn the evidence into one simple chart: {takeaway}",
                viewer_test="A viewer should understand the comparison in under three seconds.",
                scene_script="A clean editorial chart surface with one highlighted conclusion.",
                composition_script=(
                    "One chart only. Large conclusion at top, simple axes or bars, one highlighted point."
                ),
                required_elements=[
                    "one chart type",
                    "one highlighted winner or anomaly",
                    "minimal supporting labels",
                ],
                text_policy="Readable text is allowed only for the main conclusion and chart labels.",
                forbidden_elements=common_forbidden,
                compliance_checks=[
                    "Is there exactly one chart?",
                    "Is the conclusion visually highlighted?",
                    "Is there no decorative data clutter?",
                ],
            ),
            route,
            source,
        )

    if route.mode == VisualProximityMode.PERSON_STORY:
        return _with_linkedin_lens(
            VisualProductionPlan(
                plan_id=plan_id,
                route_mode=route.mode,
                concept=f"Show the human moment behind: {takeaway}",
                viewer_test="A viewer should understand who is deciding and what artifact caused the decision.",
                scene_script=(
                    "One believable founder/operator/reviewer moment. The person is reacting to a concrete "
                    "artifact, not posing for a generic office photo."
                ),
                composition_script=(
                    "Person on one side, decision artifact on the other. Use posture, gaze, or hand position "
                    "to show the moment of judgment."
                ),
                required_elements=[
                    "one human decision-maker",
                    "one concrete artifact",
                    "visible moment of pause, pointing, marking, or choosing",
                ],
                text_policy="Avoid readable text except one short marked line or simple annotation if needed.",
                forbidden_elements=common_forbidden,
                compliance_checks=[
                    "Is there a real story moment?",
                    "Is the artifact visible?",
                    "Does it avoid generic corporate stock-photo energy?",
                ],
            ),
            route,
            source,
        )

    if route.mode == VisualProximityMode.OBJECT_METAPHOR:
        return _with_linkedin_lens(
            VisualProductionPlan(
                plan_id=plan_id,
                route_mode=route.mode,
                concept=f"Use one physical metaphor for: {takeaway}",
                viewer_test="A viewer should be able to explain the metaphor in one sentence.",
                scene_script="One hero object or small object arrangement, directly mapped to the idea.",
                composition_script="Single focal point, clear negative space, no secondary metaphors competing.",
                required_elements=[
                    "one hero metaphor object",
                    "a visible tension or imbalance",
                    "simple environment that does not steal attention",
                ],
                text_policy="No readable text unless the object itself requires a short real-world label.",
                forbidden_elements=common_forbidden,
                compliance_checks=[
                    "Is there one metaphor only?",
                    "Can the metaphor be explained in one sentence?",
                    "Is the scene not just a pretty object collection?",
                ],
            ),
            route,
            source,
        )

    if route.mode == VisualProximityMode.PRODUCT_SCENE:
        return _with_linkedin_lens(
            VisualProductionPlan(
                plan_id=plan_id,
                route_mode=route.mode,
                concept=f"Show the product behavior behind: {takeaway}",
                viewer_test="A viewer should see what changed in the product or review surface.",
                scene_script=(
                    "A plausible product/review interface shown as a work surface. The state change or "
                    "decision reason must be visible."
                ),
                composition_script=(
                    "Screen or board as the hero. Use one selected item, one reason panel, and one outcome state."
                ),
                required_elements=[
                    "one selected content/review item",
                    "one visible reason or fit signal",
                    "one decision state",
                ],
                text_policy="Use abstract UI blocks or a few intentional labels only. No fake paragraphs.",
                forbidden_elements=common_forbidden,
                compliance_checks=[
                    "Is the product job visible?",
                    "Is the reason shown next to the item?",
                    "Is the UI plausible and not random widgets?",
                ],
            ),
            route,
            source,
        )

    return _with_linkedin_lens(
        VisualProductionPlan(
            plan_id=plan_id,
            route_mode=route.mode,
            concept=f"Make the thesis itself the visual: {takeaway}",
            viewer_test="A viewer should understand the thesis without any caption.",
            scene_script="A precise editorial thesis card with no illustrative scene.",
            composition_script="Large thesis, one support line, restrained accent, strong negative space.",
            required_elements=[
                "one exact thesis",
                "one short support line",
                "clear type hierarchy",
            ],
            text_policy="Readable text is required, but only the planned thesis and support line.",
            forbidden_elements=common_forbidden,
            compliance_checks=[
                "Is the text legible?",
                "Is the thesis exact?",
                "Is there no decorative filler?",
            ],
        ),
        route,
        source,
    )


def _takeaway(source: Any, fallback: str) -> str:
    if isinstance(source, dict):
        return str(source.get("intended_takeaway") or source.get("topic") or fallback)
    return str(
        getattr(source, "intended_takeaway", None) or getattr(source, "topic", None) or fallback
    )


def _piece_id(source: Any) -> str:
    if isinstance(source, dict):
        return str(source.get("piece_id") or source.get("id") or "visual")
    return str(getattr(source, "piece_id", "visual"))


def _with_linkedin_lens(
    plan: VisualProductionPlan,
    route: VisualConceptRoute,
    source: Any,
) -> VisualProductionPlan:
    return apply_linkedin_impact_lens(plan, route, source)
